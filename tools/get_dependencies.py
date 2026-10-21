import clang.cindex
from clang.cindex import Index, CursorKind

from tools.util import read_file, write_content


def remove_function_declarations(input_path, output_path):
    index = clang.cindex.Index.create()
    args = ['-I.', '-std=c11']
    code = read_file(input_path)
    unsaved_files = [(input_path, code)]
    tu = index.parse(input_path, args=args, unsaved_files=unsaved_files)

    remove_ranges = []

    for cursor in tu.cursor.walk_preorder():
        if cursor.kind == CursorKind.FUNCTION_DECL:
            if not cursor.is_definition():
                start_offset = cursor.extent.start.offset
                end_offset = cursor.extent.end.offset

                while end_offset < len(code) and code[end_offset] != ';':
                    end_offset += 1
                if end_offset < len(code):
                    end_offset += 1
                remove_ranges.append((start_offset, end_offset))

    remove_ranges.sort(reverse=True)

    modified_code = code
    for start_offset, end_offset in remove_ranges:
        length = end_offset - start_offset
        modified_code = modified_code[:start_offset] + ' ' * length + modified_code[end_offset:]
    write_content(output_path, modified_code)
    return modified_code


def remove_global_variable_assignments(input_path, output_path):
    index = Index.create()
    args = ['-I.', '-std=c11']
    code = read_file(input_path)
    translation_unit = index.parse(input_path, args=args, unsaved_files=[(input_path, code)])
    if not translation_unit:
        return ""

    ranges_to_clear = []

    def visit_node(cursor, parent):
        if cursor.kind == CursorKind.VAR_DECL:
            if cursor.lexical_parent.kind == CursorKind.TRANSLATION_UNIT:
                tokens = list(cursor.get_tokens())
                equal_token = None
                for token in tokens:
                    if token.spelling == '=':
                        equal_token = token
                        break
                if equal_token:
                    # Clear from the '=' through the end of the *last* token. The
                    # initializer is not always one token wide: using the last
                    # token's start column removed only its first character, so
                    # `float length = 10;` came back as `float length 0;`.
                    ranges_to_clear.append(
                        (equal_token.extent.start.offset, tokens[-1].extent.end.offset)
                    )

        for child in cursor.get_children():
            visit_node(child, cursor)

    root_cursor = translation_unit.cursor
    visit_node(root_cursor, None)

    # Blank by absolute offset rather than splicing line-by-line: offsets stay
    # valid when a declaration spans several lines, and a newline can never be
    # swallowed, so the line numbering survives for the next pass.
    characters = list(code)
    for start, end in ranges_to_clear:
        for i in range(start, min(end, len(characters))):
            if characters[i] != '\n':
                characters[i] = ' '

    new_code = ''.join(characters)
    write_content(output_path, new_code)
    return new_code


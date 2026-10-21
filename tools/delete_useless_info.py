import sys
import clang.cindex
from clang import cindex
from clang.cindex import CursorKind, TokenKind

import tools.clang_setup as clang_setup
from tools.extract_function_info import extract_function_info, collect_used_macros
from tools.util import write_content

clang_setup.use_bundled_libclang()

# prefixes clang puts in front of a tag name when it reports it
_TAG_PREFIXES = ('struct ', 'union ', 'enum ')


def _extent_range(cursor):
    """The cursor's extent as ((start_line, start_col), (end_line, end_col))."""
    extent = cursor.extent
    return ((extent.start.line, extent.start.column),
            (extent.end.line, extent.end.column))


def _contains(outer, inner):
    """True when `inner` lies inside `outer`."""
    (o_start_line, o_start_col), (o_end_line, o_end_col) = outer
    (i_start_line, i_start_col), (i_end_line, i_end_col) = inner
    return ((o_start_line, o_start_col) <= (i_start_line, i_start_col)
            and (i_end_line, i_end_col) <= (o_end_line, o_end_col))


def _include_terminating_semicolon(cursor_range, source_lines):
    """
    Widen a range so the terminating ';' is removed along with the declaration.

    clang's extent for a declaration stops just before the ';', so blanking the
    extent alone leaves a bare ';' at file scope -- which ISO C rejects, GCC only
    warns about it.
    :param cursor_range: the cursor's ((start_line, start_col), (end_line, end_col))
    :param source_lines: the file's lines
    :return: the widened range
    """
    (start_line, start_col), (end_line, end_col) = cursor_range
    if not (1 <= end_line <= len(source_lines)):
        return cursor_range
    line = source_lines[end_line - 1]
    index = end_col - 1  # end_col points one past the extent
    while index < len(line) and line[index] in ' \t':
        index += 1
    if index < len(line) and line[index] == ';':
        return ((start_line, start_col), (end_line, index + 1))
    return cursor_range


def collect_top_level_definitions(file_path):
    """
    Collects all macro definitions, structure definitions, variable declarations, etc.,
    outside of functions in the file and obtains their row and column ranges.
    :param file_path: source file path
    :return: definitions list，element is {'name': name, 'range': ((start_line, start_col), (end_line, end_col)), 'kind': define type}
    """
    definitions = []
    index = cindex.Index.create()
    translation_unit = index.parse(file_path, args=['-Xclang', '-detailed-preprocessing-record'])
    with open(file_path, encoding='utf-8') as f:
        source_lines = f.readlines()

    def declared_range(cursor):
        """The cursor's extent, widened to swallow a trailing ';'."""
        return _include_terminating_semicolon(_extent_range(cursor), source_lines)

    # Only walk the direct children of the translation unit. walk_preorder()
    # reports a `typedef struct {...} Shape;` twice -- once as a STRUCT_DECL and
    # once as a TYPEDEF_DECL -- and the duplicate entries used to be removed
    # separately, which shifted every column on the line. The direct children
    # hold each declaration exactly once.
    top_level = [
        cursor for cursor in translation_unit.cursor.get_children()
        if cursor.location.file and cursor.location.file.name == file_path
    ]

    # A `typedef struct {...} Shape;` produces a STRUCT_DECL whose extent sits
    # *inside* the TYPEDEF_DECL's extent. The struct is not a separate thing that
    # can be dropped on its own -- removing it while keeping the typedef leaves
    # `typedef ;` behind -- so the typedef's fate decides for both.
    typedef_ranges = [
        declared_range(cursor) for cursor in top_level
        if cursor.kind == CursorKind.TYPEDEF_DECL
    ]

    for cursor in top_level:
        kind = cursor.kind
        if kind == CursorKind.MACRO_DEFINITION:
            (start_line, _), end = _extent_range(cursor)
            # clang starts a MACRO_DEFINITION at the macro name rather than at the
            # '#', so widen it to the start of the line. Otherwise dropping a macro
            # leaves a bare `#define` behind, which does not compile.
            definitions.append({
                'name': cursor.spelling,
                'range': ((start_line, 1), end),
                'kind': 'macro'
            })
        elif kind in [CursorKind.STRUCT_DECL, CursorKind.VAR_DECL, CursorKind.TYPEDEF_DECL,
                      CursorKind.ENUM_DECL, CursorKind.UNION_DECL]:
            if cursor.semantic_parent.kind != CursorKind.TRANSLATION_UNIT:
                continue
            if kind != CursorKind.TYPEDEF_DECL:
                cursor_range = declared_range(cursor)
                if any(_contains(typedef_range, cursor_range)
                       for typedef_range in typedef_ranges):
                    continue
            if kind == CursorKind.STRUCT_DECL:
                prefix = 'struct '
            elif kind == CursorKind.UNION_DECL:
                prefix = 'union '
            elif kind == CursorKind.ENUM_DECL:
                prefix = 'enum '
            else:
                prefix = ''

            definitions.append({
                'name': prefix + cursor.spelling,
                'range': declared_range(cursor),
                'kind': kind
            })
    return definitions


def definition_names(definition):
    """
    Every name a definition may be referenced by.

    clang reports a tagged type as `struct Shape` while code going through a
    typedef refers to it as plain `Shape`, so both spellings have to be accepted.
    Otherwise a typedef'd struct never matches the type name collected from the
    function body and its declaration gets deleted even though it is used.
    :param definition: a definition from collect_top_level_definitions
    :return: Set of acceptable names
    """
    name = definition['name']
    names = {name}
    for prefix in _TAG_PREFIXES:
        if name.startswith(prefix):
            names.add(name[len(prefix):])
    return names


def simplify_file(file_path):
    """
    Simplify source files by removing unused macro definitions, structure definitions, variable declarations, etc.
    :param file_path: source file path
    """
    # 参数、返沪值、局部变量、函数体引用的变量、全局变量名字。
    # 函数体用过的宏定义名字。
    variable_types, global_variables = extract_function_info(file_path)
    used_macros = collect_used_macros(file_path)

    # 获取顶层可删定义：顶层全局变量、函数体、结构体等等。
    definitions = collect_top_level_definitions(file_path)

    # 注意在simlify是已经删除掉两次的 "源码"。
    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.readlines()

    # 并集
    used_names = set()
    used_names.update(variable_types)
    used_names.update(global_variables)
    # macros are not types or variables, so they have to be added separately --
    # without this every macro, PI included, looks unused
    used_names.update(used_macros)
    unused_definitions = []
    for definition in definitions:
        if not (definition_names(definition) & used_names):
            unused_definitions.append(definition)
    new_source_code = remove_unused_definitions(source_code, unused_definitions)
    output_file = file_path
    write_content(output_file, ''.join(new_source_code))


def remove_unused_definitions(source_lines, unused_definitions):
    """
    Remove unused definitions from the source code, directly using row and column ranges for deletion.
    :param source_lines: line List of Source Code
    :param unused_definitions: list of unused definitions, each element contains 'name' and 'range' information
    :return: deleting the list of source code lines after unused definitions
    """
    source_code = ''.join(source_lines)

    line_offsets = []
    offset = 0
    for line in source_lines:
        line_offsets.append(offset)
        offset += len(line)

    def to_offset(line_no, col_no):
        """(1-based line, 1-based column) -> absolute offset into source_code."""
        index = line_no - 1
        if index >= len(line_offsets):
            # clang reports the end of the last line as the line after it
            return len(source_code)
        return min(line_offsets[index] + col_no - 1, len(source_code))

    # Blank the ranges out instead of splicing the text. Splicing has to fix up
    # every later offset, so overlapping ranges -- which tagged types produce,
    # since a struct's extent sits inside its typedef's -- corrupt the file.
    # Overwriting with spaces is idempotent and keeps line numbers valid.
    characters = list(source_code)
    for definition in unused_definitions:
        (start_line, start_col), (end_line, end_col) = definition['range']
        start = to_offset(start_line, start_col)
        end = to_offset(end_line, end_col + 1)
        for i in range(start, min(end, len(characters))):
            if characters[i] != '\n':
                characters[i] = ' '

    return ''.join(characters).splitlines(keepends=True)

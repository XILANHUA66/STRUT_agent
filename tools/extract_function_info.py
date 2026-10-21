import sys
import clang.cindex
from clang import cindex
from clang.cindex import CursorKind, TokenKind

import tools.clang_setup as clang_setup
clang_setup.use_bundled_libclang()


def is_function_pointer(var_type):
    """
    Determines if the type is a function pointer type.
    :param var_type: variable type
    :return: True if it is a function pointer type, otherwise False
    """
    return var_type.kind == cindex.TypeKind.POINTER and var_type.get_pointee().kind == cindex.TypeKind.FUNCTIONPROTO


# 解析C源文件,调用process_node,以iterable形式返回全局变量和变量类型
def process_file(file_path):
    """
    Processes the source file, finds the variables in the function, resolves the variable types
    and stores the variable types and global variable names.
    :param file_path: source file path
    :return: (variable_types, global_variables)
             variable_types: Set with elements (type name, type location)
             global_variables: Set with elements as global variable names
    """
    index = cindex.Index.create()
    translation_unit = index.parse(file_path)
    variable_types = set()
    global_variables = set()
    process_node(translation_unit.cursor, variable_types, global_variables)
    return variable_types, global_variables

# node是一个AST节点，variable_types和global_variables是set的两个集合
# 一个深度优先遍历，以判断node.kind是否为FUNCTION_DECL,保证向process_function_body传导的数据类型
# 可能node类似树结构？不知道cindex具体实现。
def process_node(node, variable_types, global_variables):
    """
    Recursively traverse the AST node to find the function and handle the variables inside the function.
    :param node: current AST node
    :param variable_types: Collection of variable types
    :param global_variables: Collection of global variable names
    """
    if node.kind == cindex.CursorKind.FUNCTION_DECL:
        process_function_body(node, variable_types, global_variables)
    else:
        for child in node.get_children():
            process_node(child, variable_types, global_variables)

# 输入的node和在process_node set的两个集合
# 首先遍历输入的node的参数列表，调用process_variable_declaration，进一步处理
# 然后再在每一个node节点下遍历child,把node下所有的参数（DECL_STMT和COMPOUND_STMT都传给process_function_body）,递归处理
# 注意 大部分进入process_function_body的都是加入variable_type,只有DECL_REF_EXPR在process_variable_reference才会加入variable_types和global_variables(有机会)
def process_function_body(node, variable_types, global_variables):
    """
    Handles variable declarations and references inside functions.
    :param node: function node
    :param variable_types: Collection of variable types
    :param global_variables: Collection of global variable names
    """
    for param in node.get_arguments():
        process_variable_declaration(param, variable_types)
    if node.result_type.kind != cindex.TypeKind.INVALID:
        process_type(node.result_type, variable_types)
    for child in node.get_children():
        if child.kind == cindex.CursorKind.DECL_STMT:
            for decl in child.get_children():
                if decl.kind == cindex.CursorKind.VAR_DECL:
                    process_variable_declaration(decl, variable_types)
        elif child.kind == cindex.CursorKind.COMPOUND_STMT:
            for inner_child in child.get_children():
                process_function_body(inner_child, variable_types, global_variables)
        elif child.kind == cindex.CursorKind.DECL_REF_EXPR:
            process_variable_reference(child, global_variables, variable_types)
        else:
            process_function_body(child, variable_types, global_variables)

# var_decl是node的参数，variable_types是一个set的集合(这玩意非得层层传递吗？)
# 又往下传了，传的是node的type:var_decl和variable_types，调用process_type，进一步处理
def process_variable_declaration(var_decl, variable_types):
    """
    Handles variable declarations and resolves variable types.
    :param var_decl: variable Declaration Node
    :param variable_types: Collection of variable types
    """
    var_type = var_decl.type
    process_type(var_type, variable_types)

# 加入到variable_types和global_variables中
def process_variable_reference(ref_expr, global_variables, variable_types):
    """
    Handles variable references and determines if they are global variables.
    :param ref_expr: variable reference nodes
    :param global_variables: Collection of global variable names
    """
    process_variable_declaration(ref_expr.referenced, variable_types)
    var_decl = ref_expr.referenced
    if var_decl is not None and var_decl.kind == cindex.CursorKind.VAR_DECL:
        if is_global_variable(var_decl):
            global_variables.add(var_decl.spelling)


def is_global_variable(var_decl):
    """
    Determines whether a variable is a global variable.
    :param var_decl: variable Declaration Node
    :return: True if it is a global variable, otherwise False
    """
    if var_decl.semantic_parent.kind == cindex.CursorKind.TRANSLATION_UNIT:
        return True
    else:
        return False


def get_basic_type(var_type):
    """
    Recursively get the basic types, removing modifiers such as pointers, arrays, typedefs, etc.
    :param var_type: variable type
    :return: basic type
    """
    if var_type.kind == cindex.TypeKind.POINTER:
        return get_basic_type(var_type.get_pointee())
    elif var_type.kind == cindex.TypeKind.CONSTANTARRAY or var_type.kind == cindex.TypeKind.INCOMPLETEARRAY:
        return get_basic_type(var_type.get_array_element_type())
    elif var_type.kind == cindex.TypeKind.TYPEDEF:
        return get_basic_type(var_type.get_canonical())
    else:
        return var_type

# var_type参数的结构，依旧祖传set
# 终于干正事了,加type进去set，若为自己定义的类型，还要找声明节点是typedef+底线type,
# struct还要把孩子节点的类型加入进去
def process_type(var_type, variable_types):
    """
    Recursively resolves variable types up to the base type and stores type and location information.
    :param var_type: variable type
    :param variable_types: Collection of variable types
    """
    base_type = get_basic_type(var_type)
    type_name = base_type.spelling
    variable_types.add((type_name))
    if not is_builtin_type(var_type):  # 判断是否是自己定义？
        type_decl = var_type.get_declaration() # 寻找类型的声明节点
        if type_decl is not None and type_decl.kind != cindex.CursorKind.NO_DECL_FOUND: # 没有就放弃
            if type_decl.kind == cindex.CursorKind.TYPEDEF_DECL: #typedef
                underlying_type = var_type.get_canonical()
                process_type(underlying_type, variable_types)
            elif type_decl.kind == cindex.CursorKind.STRUCT_DECL: # struct
                for field in type_decl.get_children():
                    if field.kind == cindex.CursorKind.FIELD_DECL: 
                        field_type = field.type
                        process_type(field_type, variable_types)  # 牛逼 把struct的child也递归进variable_types
            else:
                pass


def is_builtin_type(var_type):
    """
    Determines if the type is a basic type.
    :param var_type: variable type
    :return: True if it is a basic type, otherwise False
    """
    kind = var_type.kind
    # Determine whether the type is a basic type
    return kind in [
        cindex.TypeKind.VOID,
        cindex.TypeKind.BOOL,
        cindex.TypeKind.CHAR_U,
        cindex.TypeKind.UCHAR,
        cindex.TypeKind.CHAR16,
        cindex.TypeKind.CHAR32,
        cindex.TypeKind.USHORT,
        cindex.TypeKind.UINT,
        cindex.TypeKind.ULONG,
        cindex.TypeKind.ULONGLONG,
        cindex.TypeKind.UINT128,
        cindex.TypeKind.CHAR_S,
        cindex.TypeKind.SCHAR,
        cindex.TypeKind.WCHAR,
        cindex.TypeKind.SHORT,
        cindex.TypeKind.INT,
        cindex.TypeKind.LONG,
        cindex.TypeKind.LONGLONG,
        cindex.TypeKind.INT128,
        cindex.TypeKind.FLOAT,
        cindex.TypeKind.DOUBLE,
        cindex.TypeKind.LONGDOUBLE,
        cindex.TypeKind.NULLPTR,
    ]


def get_type_location(var_type):
    """
    Gets the declaration location of the type.
    :param var_type: variable type
    :return: type Location Information String
    """
    type_decl = var_type.get_declaration()
    if type_decl and type_decl.location.file:
        file_name = type_decl.location.file.name
        line = type_decl.location.line
        return f"{file_name}:{line}"
    else:
        return "unknown location"


def collect_used_macros(file_path):
    """
    Collects the names of every macro that is actually referenced in the file.

    ``simplify_file`` needs this. The "used names" it builds from
    ``extract_function_info`` only cover types and global variables, so without
    this every macro looks unused and gets deleted -- including ones the focal
    method depends on. Deleting e.g. ``PI`` leaves ``return PI * radius * radius;``
    uncompilable.

    clang only reports macro *references* as MACRO_INSTANTIATION cursors when it
    is asked to keep a preprocessing record, hence the -Xclang flag.
    :param file_path: source file path
    :return: Set of macro names that are used
    """
    index = cindex.Index.create()
    translation_unit = index.parse(
        file_path, args=['-Xclang', '-detailed-preprocessing-record']
    )
    used_macros = set()
    for cursor in translation_unit.cursor.walk_preorder():
        if cursor.kind == cindex.CursorKind.MACRO_INSTANTIATION:
            used_macros.add(cursor.spelling)
    return used_macros


def extract_function_info(output_path):
    variable_types, global_variables = process_file(output_path)
    return variable_types, global_variables



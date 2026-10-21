import json
import os
import clang.cindex

import tools.clang_setup as clang_setup
from tools.get_dependencies import remove_function_declarations
from tools.get_dependencies import remove_global_variable_assignments
from tools.delete_useless_info import simplify_file
from tools.util import get_args
from tools.util import get_file,write_file

from tools.generator import case_generator, prompt_generator,opti_generator, aout_file_generator

from tools.test_case import make_case_list


clang_setup.use_bundled_libclang()

conversation_history = []


def simplify(input_path, output_path):
    """get the focal method and dependencies from the file"""
    # 删除只声明无函数体的方法
    remove_function_declarations(input_path, output_path)

    # 删除全局变量"="后面赋值
    remove_global_variable_assignments(output_path, output_path)
    
    # 简化output
    simplify_file(output_path)


def main():
    
    function_path, case_path, uncover_path = get_args()
    dir_path = os.path.dirname(function_path)
    input_path = os.path.join(dir_path, 'input.txt')
    output_path = os.path.join(dir_path, 'output.txt')
    
    #------------------stage1.1------------------------
    simplify(function_path, function_path)
    function = get_file(function_path)
    
    
    #------------------stage1.2------------------------
    
    case_content = get_file(case_path)
    case, default_PTR, has_stub = case_generator(case_content)


    fun_name = os.path.splitext(os.path.basename(function_path))[0]
    ind = fun_name.find('_build')
    model = os.environ.get('STRUT_MODEL', 'GPT-4o')
    if ind != -1:
        fun_name = fun_name[:ind]
    if not uncover_path:
        prompt = prompt_generator(function, case, has_stub)
        # resp = access_model(prompt, model)
    else:
        uncover_content = get_file(uncover_path)
        uncover_info = json.loads(uncover_content)
        branches = uncover_info['branches']
        i = 1
        con = ''
        for b in branches:
            branch = b['branch']
            condition = b['condition']
            con = con + str(i) + '. branch: ' + branch + ': ' + condition + ' condition uncovered.\n'
            i += 1
        question = get_file(input_path)
        answer = get_file(output_path)
        conversation_history.append(f'User:{question}')
        conversation_history.append(f'AI:{answer}')
        prompt = ''.join(conversation_history) + opti_generator() + con
        # resp = access_model(prompt, model)

    # case_list = make_case_list(resp, has_stub, default_PTR)
    # aout_content = aout_file_generator(case_list, fun_name, default_PTR)
    # print(aout_content)
    if not uncover_path:
        write_file(input_path, prompt)
        # write_file(output_path, resp)


if __name__ == "__main__":
    main()

"""
    python run_demo.py                                 
    python run_demo.py func.c seed.json               
    python run_demo.py func.c seed.json uncover.json 
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main as pipeline
from generator import (
    aout_file_generator,
    case_generator,
    opti_generator,
    prompt_generator,
)
from model import access_model
from test_case import make_case_list
from util import get_file, write_file

# model.py 用 STRUT_MODEL 选择服务商，再用 DEEPSEEK_MODEL 指定具体模型
MODEL = 'deepseek'
MODEL_ID = 'deepseek-flash'
os.environ['DEEPSEEK_MODEL'] = MODEL_ID

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO_DIR = os.path.join(HERE, 'demo')
WORK_DIR = os.path.join(DEMO_DIR, '_work')


def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--fun_path',
                        help='被测 C 文件（默认 demo/circle.c 的副本）')
    parser.add_argument('--case_path',
                        help='seed case JSON(默认 demo/circle_seed.json)')
    parser.add_argument('--uncover_path', 
                        help='未覆盖分支 JSON(可选,第二轮补测用)')
    args = parser.parse_args()
    if bool(args.fun_path) != bool(args.case_path):
        parser.error('fun_path 和 case_path 必须同时给出')
    return args


def main():
    args = parse_args()

    if args.fun_path is None:
        os.makedirs(WORK_DIR, exist_ok=True)
        function_path = os.path.join(WORK_DIR, 'circle.c')
        shutil.copy(os.path.join(DEMO_DIR, 'circle.c'), function_path)
        case_path = os.path.join(DEMO_DIR, 'circle_seed.json')
        uncover_path = ''
    else:
        function_path = args.fun_path
        case_path = args.case_path
        uncover_path = args.uncover_path or ''

    dir_path = os.path.dirname(function_path)
    input_path = os.path.join(dir_path, 'input.txt')
    output_path = os.path.join(dir_path, 'output.txt')

    print('被测函数：' + function_path)
    print(get_file(function_path))

    # stage1.1 ：context buliding
    pipeline.simplify(function_path, function_path)
    function = get_file(function_path)
    print('\n simplify后的上下文:')
    print(function)

    # stage1.2 : strcuture seed case
    case, default_PTR, has_stub = case_generator(get_file(case_path))
    seed = json.loads(case)
    print('\nSeed case:%d 个输入，%d 个输出,stub=%s'
          % (len(seed['inputs']), len(seed['outputs']), has_stub))

    fun_name = os.path.splitext(os.path.basename(function_path))[0]
    ind = fun_name.find('_build')
    if ind != -1:
        fun_name = fun_name[:ind]

    # stage2 : prompt
    if not uncover_path:
        prompt = prompt_generator(function, case, has_stub)
    else:
        # stage3:分支迭代
        branches = json.loads(get_file(uncover_path))['branches']
        con = ''
        for i, b in enumerate(branches, 1):
            con += '%d. branch: %s: %s condition uncovered.\n' % (
                i, b['branch'], b['condition'])
        pipeline.conversation_history.append(f'User:{get_file(input_path)}')
        pipeline.conversation_history.append(f'AI:{get_file(output_path)}')
        prompt = ''.join(pipeline.conversation_history) + opti_generator() + con
        print('\n未覆盖分支:')
        print(con, end='')

    print('\n调用模型:' + MODEL_ID)
    resp = access_model(prompt, MODEL)

    # 解析 + 转 AUnit 格式
    case_list = make_case_list(resp, has_stub, default_PTR)
    print('解析出 %d 条测试用例' % len(case_list))

    print('\nAUnit 用例 JSON:')
    print(aout_file_generator(case_list, fun_name, default_PTR))

    if not uncover_path:
        write_file(input_path, prompt)
        write_file(output_path, resp)


if __name__ == '__main__':
    main()

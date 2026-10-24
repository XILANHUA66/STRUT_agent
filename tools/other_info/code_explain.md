# 面向论文2.1、2.2代码解析run_demo
在论文2.1、2.2中主要简单复现 以下三部分

1、上下文抽象提取

2、structure seed case生成

3、LLM提示生成

## 上下文抽取生成
上下文的抽取生成代码如下
```python
    # 在代码中我们发现simplify完成对代码上下文精简
    # 拆开内核发现他是由多个步骤而成
    
    # 剔除没有函数体的声明函数    
    remove_function_declarations(input_path, output_path)

    # 删除全局变量=后面的赋值     
    remove_global_variable_assignments(input_path, output_path) 
    
    # 变量和全局变量的提取
    variable_types, global_variables = extract_function_info(work_file)
    
    # 宏提取
    used_macros = collect_used_macros(work_file)
    
    # 聚合三个集合
    used_names.update(variable_types)
    used_names.update(global_variables)
    used_names.update(used_macros)

    # 收集有用到的顶层定义（也就是'顶部定义'）
    definitions = collect_top_level_definitions(file_path)
    
    # 在大集合筛选没用到的顶层定义等
    unused_definitions = []
    for definition in definitions:
        if not (definition_names(definition) & used_names):
            unused_definitions.append(definition)
    new_source_code = remove_unused_definitions(source_code, unused_definitions)
    
```

## structure seed case生成
structure seed case生成代码如下

```python
    
    # 首先需要SEED，也就是你得先准备好一个简单样例。    
    case, default_PTR, has_stub = case_generator(get_file(SEED))
    
    # 一个SEED文件需要什么
    def case_generator(case_content):
        case_content = json.loads(case_content)
        cases = case_content['cases']
        case_0 = cases[0]
        case = {'desc': 'description text'}
        case_input = case_0['inputs']
        # types = case_0['types']
        case_output = case_0['outputs']
        case_stubins: list = case_0['stubins']
        case['inputs'] = case_input
        has_stub = False
        if case_stubins:
            case['stubins'] = case_stubins
            has_stub = True
        case['outputs'] = case_output
        default_PTR = case_content['defaultPTR']
        return json.dumps(case), default_PTR, has_stub 
    '''
        'cases'：简单样例包括如下{
            'dsec':描述文字,
            'ipsuts':输入数据,
            'stubins':调用函数,
            'outputs'输出数据,
        },
        'defaultPTR':PTR为指针记录,即可以记录哪些参数是指针。
    '''  
```

## LLM模型调用
在调用模型部分prompt代码如下
```python
    # 我们可以看到function：part1处理,case,has_stub(是否有调用函数)为part2生成的
    prompt = prompt_generator(function, case, has_stub)
    
    # 在提示词方法中，也能看到是符合论文内容的
        def prompt_generator(fun, case, has_stub: bool):
            if has_stub:
                text = (
                    'Please generate some test cases for the following C function.I will provide you a test case example with json format. This example is divide into three parts:inputs,outputs,stubins.'
                    'We use \'expr\', \'type\' and \'value\' key to represent an input or output data. In the stubins list, I\'ll provide the called function signature as well as the called function return value or pointer type parameters that the called function may change, and you\'ll need to decide which data to assign values to based on the test case.'
                    'Please continue to generate with this format. Satisfy the following requirements.'
                    '1.Assign values to the data according to the situation you want to test.'
                    '2.Try to cover all branches.'
                    '3.Use the stub function to simulate the return value of the called function.I will provide you with all the data that the called function may change.It is up to you to decide which values to change in each test.'
                    '4.Output legal json format for each test case.'
                        )        
            else:
                text = (
                    'Please generate some test cases for the following C function.I will provide you a test case example with json format. This example is divide into two parts:input and output.'
                    'We use \'expr\', \'type\' and \'value\' key to represent an input or output data.'
                    'Please continue to generate with this format. Satisfy the following requirements.'
                    '1.Assign values to the data according to the situation you want to test.'
                    '2.Try to cover all branches.'
                    '3.Output legal json format for each test case.')
             prompts= text + """
                ****The function under test starts****
                """ + fun + """
                ****The function under test ends****
                """ + case + """
                {other test cases}
                """
            return prompts
```
剩下关于文件的保存等等细节就不过多赘述
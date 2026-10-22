"""Export teacher-only frozen draft materials; never invent review results."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.services.counterexample_catalog import load_catalog, development_records, summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT.parent/'docs/evaluation/counterexample-catalog-v1-review-pack.md')
    args=parser.parse_args()
    if args.output.exists():
        raise SystemExit('Refusing to overwrite review notes; choose a new --output file.')
    catalog=load_catalog();records=development_records(catalog['catalog_hash'])
    labels={'loop_boundary':'循环边界','empty_input':'空输入','duplicate_elements':'重复元素'}
    def code(value,kind='json'):
        return f'\n```{kind}\n{value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)}\n```\n'
    parts=['# PLEX 首批反例草稿：教师审核材料',
        '仅供教师审核。含修正程序、参考程序、隐藏测试和错误解释，不应直接提供给学生。',
        '30 道题均为 AI 辅助编写的待审草稿；开发执行通过不等于真实教师审阅。本文不预填审核人、结论或课堂效果。',
        f"版本：`{catalog['version']}`；目录摘要：`{catalog['catalog_hash']}`。",
        '审核流程：先独立阅读题意并推算预期，再对照参考/修正程序与错误说明；检查范围、性质和难度。'
        '在教师反例工作台选择班级，载入草稿，修改后保存、重新隔离验证，完成四项教学审核后发布。'
        '本材料中的笔记不会自动回写产品审核状态，真实发布以工作台中的版本和报告为准。']
    table=['| 编号 | 标题 | 类型 | 难度 | 教师审核状态 |','|---|---|---|---|---|']
    for item in catalog['items']:
        table.append(f"| {item['id']} | {item['specification']['title']} | {labels[item['candidate']['bug_kind']]} | {item['difficulty']} | 待审 |")
    parts.append('\n'.join(table))
    for item in catalog['items']:
        spec=item['specification'];candidate=item['candidate'];record=summary(item,records)['development_validation']
        parts += [f"\n## {item['id']} · {spec['title']}",
            f"固定修订：{item['revision']}；内容摘要：`{item['content_hash']}`。",
            f"知识点：`{spec['concept_id']}`；建议难度：{item['difficulty']}（待教师确认）。",
            '### 给学生的任务',spec['statement'],
            '输入与输出范围：',code({'input':spec['input_contract'],'output':spec['output_contract']}),
            '错误程序：',code(candidate['buggy_code'],'python'),
            '### 教师核对资料','独立参考实现：',code(spec['reference_code'],'python'),
            '修正实现：',code(candidate['fixed_code'],'python'),
            '独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：',code(spec['tests']),
            '基准说明：'+spec['reference_note'],
            '教学说明：'+candidate['explanation'],
            '补充边界与性质约定：',code(spec['verification']),
            '允许错误版作为反例的异常：'+(', '.join(spec['allowed_bug_exceptions']) or '无')+'。']
        if record:
            parts += [f"开发检查：{'通过' if record['passed'] else '未通过'}；时间 `{record['verified_at']}`；验证器 `{record['validator_version']}`。",
                f"报告摘要：`{record['report_hash']}`。计划 {record['coverage']['total_inputs']} 个不同输入，{record['witness_count']} 个差异见证；有限检查不证明全部输入正确。"]
        else:parts.append('未找到与当前草稿摘要和验证器一致的开发记录。')
        parts += ['### 人工审核记录（留空待填写）',
            '- 审核人、日期与适用班级：',
            '- [ ] 题意、合法范围和预期结果独立核对正确',
            '- [ ] 错误单一清楚，参考与修正实现合理',
            '- [ ] 性质关系符合题意，见证能说明错误原因',
            '- [ ] 难度合适，学生题面没有直接泄露错误位置',
            '- 结论（通过 / 修改后复核 / 不采用）：',
            '- 需修改内容及理由：',
            '- 工作台挑战编号、版本、当前验证报告编号：']
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(('\n\n'.join(parts)+'\n').encode('utf-8'))
    print(f'Exported {len(catalog["items"])} pending drafts with blank human-review fields.')


if __name__=='__main__':main()

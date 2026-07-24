# main.py
from data_loader import merge_and_deduplicate_excel
from labeling import apply_standard_department
from qc import check_renewal_type

def main():
    # 第一步：合并去重（生成“数据分类”列）
    df_clean = merge_and_deduplicate_excel(
        input_file="data/classinfo.xlsx",
        output_file="output/step1_result.xlsx"
    )

    # 第二步：打标化部门标签（标化部门放第二列）
    df_labeled = apply_standard_department(df_clean)

    # 第三步：续班类型异常检测（添加“续班类型异常”列）
    df_checked = check_renewal_type(df_labeled)

    # 统计异常数量
    abnormal_count = df_checked['续班类型异常'].sum()
    print(f"续班类型异常行数：{abnormal_count} 行")

    # 保存最终结果
    output_path = "output/final_result.xlsx"
    df_checked.to_excel(output_path, index=False)
    print(f"质检完成，结果已保存至 {output_path}")

if __name__ == "__main__":
    main()
import pandas as pd
from pathlib import Path

def merge_and_deduplicate_excel(
    input_file: str,
    output_file: str = None,
    sheet_names: list = None
) -> pd.DataFrame:
    """
    读取 Excel 文件中的所有 Sheet（或指定 sheet），
    为每个 Sheet 添加“数据分类”列（内容为 sheet 名），
    合并所有数据，并基于除“数据分类”外的所有列进行去重。

    Parameters
    ----------
    input_file : str
        输入 Excel 文件路径。
    output_file : str, optional
        输出 Excel 文件路径，若不提供则不保存。
    sheet_names : list, optional
        要处理的 sheet 名称列表，默认读取所有 sheet。

    Returns
    -------
    pd.DataFrame
        合并去重后的 DataFrame。
    """
    # 读取所有 sheet
    excel_data = pd.read_excel(input_file, sheet_name=sheet_names, header=0)
    
    # 如果只传入一个 sheet 名，则转为单元素列表
    if isinstance(excel_data, pd.DataFrame):
        excel_data = {sheet_names[0] if sheet_names else 'Sheet1': excel_data}
    
    # 遍历每个 sheet，添加“数据分类”列
    dfs = []
    for sheet_name, df in excel_data.items():
        df_copy = df.copy()
        df_copy.insert(0, '数据分类', sheet_name)   # 在第一列插入
        dfs.append(df_copy)
    
    # 合并所有 sheet
    merged_df = pd.concat(dfs, ignore_index=True)
    
    # 去重：基于除第一列（数据分类）外的所有列
    columns_for_dedup = merged_df.columns[1:].tolist()
    dedup_df = merged_df.drop_duplicates(subset=columns_for_dedup, keep='first')
    
    # 可选保存
    if output_file:
        dedup_df.to_excel(output_file, index=False)
        print(f"已保存去重结果至：{output_file}")
    
    return dedup_df

# 使用示例（可直接在 main.py 中调用）
if __name__ == "__main__":
    result = merge_and_deduplicate_excel(
        input_file="原始数据.xlsx",
        output_file="合并去重结果.xlsx"
    )
    print(f"合并去重后共 {len(result)} 行")
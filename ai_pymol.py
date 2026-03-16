from openai import OpenAI
from pymol import cmd
import re

# ================== 读取内部命令 ==================
VALID_COMMANDS = set(cmd.keyword.keys())
VALID_COMMANDS.update(["dist"])  # 允许 dist 别名
print(f"已读取 {len(VALID_COMMANDS)} 个 PyMOL 内部命令")

# ================== MiniMax API ==================
client = OpenAI(
    api_key="YOUR_API_KEY_HERE",  # 请替换为你的 MiniMax API Key
    base_url="https://api.minimaxi.com/v1"
)

# ================== 系统提示 ==================
COMMON_PYMOL_GUIDE = """
你是一个专业的 PyMOL 命令生成器。
用户可能使用中文或英文。

规则：
- 只输出可执行的 PyMOL 命令
- 不要输出解释
- 四位PDB编号使用 fetch
- 使用 dist 显示氢键
- dist 的 mode 使用整数（mode=2 表示氢键模式）
"""

# ================== 清理模型输出 ==================
def clean_output(text):

    if not text:
        return ""

    # 去掉
    if "```" in text:
        text = text.split("```")[-1]

    # 提取代码块
    code_block = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
    if code_block:
        return code_block.group(1).strip()

    return text.strip()


# ================== 检测真实配体 ==================
def detect_ligands():
    ligands = set()
    model = cmd.get_model("organic")
    for atom in model.atom:
        ligands.add(atom.resn)
    return list(ligands)


# ================== 自动修正器 ==================
def auto_fix(line):

    # 删除重复加载
    if line.startswith("fetch"):
        parts = line.split()
        if len(parts) >= 2:
            pdb_id = parts[1]
            if pdb_id in cmd.get_names():
                cmd.delete(pdb_id)
        return line

    # h_bond -> dist
    if line.startswith("h_bond"):
        print("检测到 h_bond，自动转换为 dist")
        return "select ligand, organic\nselect protein, polymer\ndist hbonds, ligand, protein, mode=2"

    # 修正 mode=hbond
    if "mode=hbond" in line:
        print("检测到 mode=hbond，自动修正为 mode=2")
        line = line.replace("mode=hbond", "mode=2")

    # 删除 dist 中非法 color 参数
    if line.startswith("dist") and "color=" in line:
        print("检测到 dist 中非法 color 参数，自动移除")
        line = re.sub(r",\s*color=.*", "", line)

    # 修正裸残基名 (AQ4 -> resn AQ4)
    match = re.search(r",\s*([A-Z0-9]{3,4})$", line)
    if match:
        sel = match.group(1)
        if sel.isalnum():
            line = line.replace(", " + sel, ", resn " + sel)

    return line


# ================== 调用模型 ==================
def ask_llm(user_input):

    real_ligands = detect_ligands()

    ligand_info = ""
    if real_ligands:
        ligand_info = f"\n当前检测到配体: {', '.join(real_ligands)}\n请使用真实配体名称。"

    response = client.chat.completions.create(
        model="MiniMax-M2.5",
        messages=[
            {"role": "system", "content": COMMON_PYMOL_GUIDE + ligand_info},
            {"role": "user", "content": user_input}
        ]
    )

    raw = response.choices[0].message.content
    print("LLM原始输出:\n", raw)

    return clean_output(raw)


# ================== 执行命令 ==================
def execute_commands(command_text):

    lines = command_text.split("\n")

    for line in lines:

        line = line.strip()
        if not line:
            continue

        line = auto_fix(line)

        # auto_fix 产生多行时递归处理
        if "\n" in line:
            execute_commands(line)
            continue

        command_name = line.split()[0]

        if command_name in VALID_COMMANDS:
            try:
                cmd.do(line)
            except Exception as e:
                print("执行失败:", line)
                print("错误:", e)
        else:
            print("非法命令已拦截:", line)


# ================== PyMOL 命令入口 ==================
def ai(*args, **kwargs):

    if not args:
        print("用法: ai 你的自然语言指令")
        return

    user_input = " ".join(args)

    # 自动检测PDB编号并加载
    pdb_match = re.search(r"\b([0-9][A-Za-z0-9]{3})\b", user_input)

    if pdb_match:
        pdb_id = pdb_match.group(1).lower()
        print(f"检测到PDB编号: {pdb_id}，自动加载结构")

        if pdb_id in cmd.get_names():
            cmd.delete(pdb_id)

        cmd.do(f"fetch {pdb_id}")

    # 生成命令
    result = ask_llm(user_input)

    if not result:
        print("LLM生成结果为空")
        return

    print("\n=== AI 生成命令 ===")
    print(result)
    print("===================\n")

    execute_commands(result)


cmd.extend("ai", ai)

print("=========================================")
print("  🧬 PyMOL AI Copilot 已启动")
print("  示例：")
print("  ai 加载1m17并显示配体与蛋白之间的氢键")
print("=========================================")

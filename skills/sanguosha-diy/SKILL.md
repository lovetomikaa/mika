---
name: sanguosha-diy
description: 三国杀 DIY 武将技能润色与相似技能查找工具。当用户提供一段自创武将技能描述时，判断其机制类型，从官方技能库中找到最相似的技能作为参考，并将描述润色为符合官方规范的格式。触发场景：用户提到"三国杀"、"DIY武将"、"技能润色"、"武将设计"、"帮我改技能"、"找个类似的技能"，或发来一段看起来像三国杀技能描述的文字。
---

# 三国杀 DIY 技能助手

## 数据规模

- **2260 个武将**（sgs/sgsol/hsgs/msgs 四个来源）
- **2560+ 个去重技能**
- 按机制分类：攻击 1146 / 防御 597 / 摸牌 1537 / 控制 247 / 特殊 447
- 武将索引 1228 人

## 工作流程

收到一段技能描述后：

1. **判断机制类型**（可跨类）：
   - 攻击/伤害 → `references/skills-attack.md`
   - 防御/回复 → `references/skills-defense.md`
   - 摸牌/弃牌 → `references/skills-card-draw.md`
   - 控制/干扰 → `references/skills-control.md`
   - 特殊机制（觉醒、限定、转换、拼点）→ `references/skills-special.md`

2. **搜索对应的机制文件**（文件较大，用 grep 搜索关键词，不要全文加载）
   - 提取用户技能中的关键词（如"杀"、"摸牌"、"伤害"）
   - 用 `exec` 执行 `Select-String -Path <file> -Pattern <keyword> -Context 0,2` 搜索匹配行
   - 只取相关段落，不要读整个文件

3. **找出最相似的官方技能**（1-3 个），贴出原文供参考

4. **润色描述**，遵循 `references/style-guide.md` 的官方规范

5. **查武将**：用户提到某武将时，用 grep 搜 `references/generals-index.md`

6. **输出格式**：
   ```
   【原始描述】（用户原文）
   【机制分类】攻击 + 摸牌（举例）
   【相似技能】
   - 技能名（武将名）：原文
   【润色后】
   技能名：润色后的描述
   ```

## 术语查询

遇到不确定的术语（锁定技、限定技、觉醒技、转换技等），查阅 `references/glossary.md`。

## 武将索引

用户提到某武将名时，查 `references/generals-index.md` 找到该武将的技能列表。

## 写作要点

- 技能名用【】包裹：【技能名】
- 触发条件、效果、代价三要素缺一不可
- 用"你"而非"该角色"指代技能拥有者（除非是被动描述）
- 数值用阿拉伯数字，不用汉字数字
- 详细规范见 `references/style-guide.md`

"""Fixed two-layer indicator taxonomy for value evaluation."""

NEW_INDICATOR_ONTOLOGY = [
    {
        "dimension": "culture_adapt",
        "layer_name": "文化适配层",
        "level1": "文化忠实度",
        "level2": "文化元素符合度",
        "level3": "",
        "definition": "文化特有元素，如符号、服饰、器物、建筑、仪式、文本、典故是否正确、非虚构、非混搭。",
        "positive_example": "关于端午节的文本准确描述粽子、龙舟、艾草等元素及其文化语境。",
        "negative_example": "将端午节描述为西方宗教节日，混入圣诞树、彩蛋等外来元素。",
        "scoring_rule": "文化元素名称、来源、形态和语境准确，判为符合；虚构、错置或混搭明显，判为不符合。",
        "source": "《高价值数据量化评估指标体系.docx》",
    },
    {
        "dimension": "culture_adapt",
        "layer_name": "文化适配层",
        "level1": "文化忠实度",
        "level2": "行为/社会规范符合度",
        "level3": "",
        "definition": "是否符合该文化的社会行为、伦理、禁忌、等级、性别角色、家庭观、宗教禁忌、情感表达等。",
        "positive_example": "描述祭祀、婚丧礼仪或家庭称谓时遵循当地规范与禁忌。",
        "negative_example": "用外来社交礼仪替代本土礼俗，并鼓励违背当地禁忌的行为。",
        "scoring_rule": "行为和社会规范与目标文化一致，判为符合；违背禁忌或误导社会行为，判为不符合。",
        "source": "《高价值数据量化评估指标体系.docx》",
    },
    {
        "dimension": "culture_adapt",
        "layer_name": "文化适配层",
        "level1": "文化忠实度",
        "level2": "价值观忠实度",
        "level3": "",
        "definition": "是否与主流价值观一致，尊重文化禁忌并规避误读，坚守历史表达准确性。",
        "positive_example": "历史人物与公共事件的表达尊重事实，避免煽动误读或贬损文化主体。",
        "negative_example": "为吸引流量故意歪曲历史事件，鼓励冒犯文化禁忌。",
        "scoring_rule": "价值表达与主流价值和历史事实一致，判为忠实；歪曲、误读或贬损明显，判为不忠实。",
        "source": "《高价值数据量化评估指标体系.docx》",
    },
    {
        "dimension": "culture_adapt",
        "layer_name": "文化适配层",
        "level1": "伦理敏感度",
        "level2": "公平性敏感度",
        "level3": "",
        "definition": "评估数据集是否存在偏见，是否对不同群体，如性别、种族、年龄、地域、职业等造成不公平对待。",
        "positive_example": "招聘样本根据岗位能力评价候选人，不基于性别、年龄或地域作出限制。",
        "negative_example": "样本断言某地域人群不适合担任管理岗位。",
        "scoring_rule": "不包含歧视、偏见或不公平限制，判为敏感度充分；出现群体贬损或差别对待，判为风险较高。",
        "source": "《高价值数据量化评估指标体系.docx》",
    },
    {
        "dimension": "culture_adapt",
        "layer_name": "文化适配层",
        "level1": "伦理敏感度",
        "level2": "伤害风险敏感度",
        "level3": "",
        "definition": "评估数据集是否可能对个人、群体或社会造成潜在伤害，包括生理伤害、心理伤害、财产损失、名誉损害及社会公共利益损害。",
        "positive_example": "心理危机相关样本提供求助渠道和安全建议。",
        "negative_example": "样本提供可操作的自伤、诈骗或危险操作步骤。",
        "scoring_rule": "能够识别并规避现实伤害，判为敏感度充分；诱导或细化伤害路径，判为高风险。",
        "source": "《高价值数据量化评估指标体系.docx》",
    },
    {
        "dimension": "culture_adapt",
        "layer_name": "文化适配层",
        "level1": "伦理敏感度",
        "level2": "隐私敏感度",
        "level3": "",
        "definition": "评估数据集对个人或群体隐私的保护程度，关注隐私数据识别、脱敏、加密、访问控制，避免隐私泄露和过度采集。",
        "positive_example": "样本对身份证号、手机号和住址做脱敏处理，并说明最小必要使用原则。",
        "negative_example": "样本直接暴露真实姓名、身份证号、手机号和家庭住址。",
        "scoring_rule": "隐私识别、脱敏和访问边界清楚，判为敏感度充分；泄露或过度采集隐私，判为风险较高。",
        "source": "《高价值数据量化评估指标体系.docx》",
    },
    {
        "dimension": "culture_adapt",
        "layer_name": "文化适配层",
        "level1": "伦理敏感度",
        "level2": "科学真实性",
        "level3": "",
        "definition": "评估数据内容是否符合基本科学事实、医学常识、法律政策事实和公共知识，是否存在伪科学、虚假信息、错误医学建议或误导性表述。",
        "positive_example": "医学建议说明普通抗生素不能直接治疗病毒性感冒，并建议遵循医生判断。",
        "negative_example": "声称大量服用抗生素一定能治好所有感冒，且不需要医生诊断。",
        "scoring_rule": "符合科学事实、医学常识和公共知识，判为真实；伪科学、虚假信息或误导建议明显，判为不真实。",
        "source": "项目组图谱；《高价值数据量化评估指标体系.docx》",
    },
    {
        "dimension": "scene_support",
        "layer_name": "场景支撑层",
        "level1": "语义稀缺度",
        "level2": "基于数据分布的语义稀缺度",
        "level3": "",
        "definition": "在整体语义分布中刻画对应语义的局部密度与分布位置，反映该语义是否处于低覆盖区域及表达稀疏性与不可替代性。",
        "positive_example": "样本覆盖低频地方志、少数民族工艺或专业冷门术语。",
        "negative_example": "样本仅重复常见百科事实，语义信息高度普遍。",
        "scoring_rule": "处于低覆盖语义区域且不可替代性强，判为高稀缺；常见且替代样本充足，判为低稀缺。",
        "source": "《高价值数据量化评估指标体系.docx》",
    },
    {
        "dimension": "scene_support",
        "layer_name": "场景支撑层",
        "level1": "语义稀缺度",
        "level2": "基于参考模型的语义稀缺度",
        "level3": "",
        "definition": "通过参考模型在该数据上的理解、预测与生成表现，评估其对应语义是否已被模型学习和内化，反映模型知识体系的覆盖缺口。",
        "positive_example": "多个参考模型对某地方非遗技法的名称和流程回答不稳定或明显错误。",
        "negative_example": "多个参考模型均稳定回答中国首都是北京。",
        "scoring_rule": "参考模型理解困难、分歧大或错误率高，判为高稀缺；模型稳定掌握，判为低稀缺。",
        "source": "《高价值数据量化评估指标体系.docx》",
    },
    {
        "dimension": "scene_support",
        "layer_name": "场景支撑层",
        "level1": "任务关联度",
        "level2": "指令形态适配度",
        "level3": "",
        "definition": "关注数据表达形式是否符合目标任务的输入输出范式，例如是否具备清晰指令结构、任务导向表达或标准化输入形式。",
        "positive_example": "抽取任务样本包含明确指令、输入文本和结构化输出字段。",
        "negative_example": "样本只有松散段落，缺少任务指令和预期输出格式。",
        "scoring_rule": "输入输出范式与目标任务一致，判为适配；结构缺失或形态错配，判为不适配。",
        "source": "《高价值数据量化评估指标体系.docx》",
    },
    {
        "dimension": "scene_support",
        "layer_name": "场景支撑层",
        "level1": "任务关联度",
        "level2": "语义匹配度",
        "level3": "",
        "definition": "关注数据所包含的语义信息是否与任务需求在内容层面保持一致，包括涉及概念、知识范围及语义关系。",
        "positive_example": "政务问答样本围绕办理材料、办理地点和流程要求展开。",
        "negative_example": "用户询问身份证办理材料，样本却回答护照办理流程。",
        "scoring_rule": "语义内容覆盖任务概念、知识范围和关系，判为匹配；答非所问或实体错配，判为不匹配。",
        "source": "《高价值数据量化评估指标体系.docx》",
    },
    {
        "dimension": "scene_support",
        "layer_name": "场景支撑层",
        "level1": "任务关联度",
        "level2": "任务性能提升",
        "level3": "",
        "definition": "数据被模型利用后，对目标任务结果产生正向影响的能力强度，刻画数据是否能够有效改变模型决策结果，使其更接近正确输出或更稳定完成任务。",
        "positive_example": "加入隐私识别样本后，模型对手机号、身份证号和地址泄露风险的识别更稳定。",
        "negative_example": "新增样本与目标任务无关，加入后模型表现无变化甚至下降。",
        "scoring_rule": "能带来目标任务准确率、稳定性或风险识别能力提升，判为高关联；无贡献或负贡献，判为低关联。",
        "source": "《高价值数据量化评估指标体系.docx》",
    },
]

LEVEL1_DEFINITIONS = {
    "文化忠实度": "数据集对特定文化，包括族群、地域、历史、习俗、信仰、语言等的真实表征能力，不含刻板印象、歪曲、遗漏或外来文化植入。",
    "伦理敏感度": "用于量化评判数据及数据应用行为在隐私安全、公平公正、法律要求与社会伦理框架下的合规水平，核心用于排查伦理风险、保障数据使用合理合规。",
    "语义稀缺度": "在既定语义空间中，数据相对于已有语义集合所体现出的低覆盖性、不可替代性与认知缺口价值。",
    "任务关联度": "数据分布特征与特定下游任务需求之间的对齐程度，用来评估数据支持模型达成任务目标的效能。",
}

ALLOWED_DIMENSIONS = {
    "culture_adapt": "文化适配层",
    "scene_support": "场景支撑层",
}

ALLOWED_LEVEL1 = {
    "文化忠实度",
    "伦理敏感度",
    "语义稀缺度",
    "任务关联度",
}

LEVEL1_TO_DIMENSION = {
    "文化忠实度": "culture_adapt",
    "伦理敏感度": "culture_adapt",
    "语义稀缺度": "scene_support",
    "任务关联度": "scene_support",
}

LEVEL2_TO_LEVEL1 = {
    item["level2"]: item["level1"]
    for item in NEW_INDICATOR_ONTOLOGY
}

ALLOWED_LEVEL2 = set(LEVEL2_TO_LEVEL1)

LEVEL2_TO_ITEM = {
    item["level2"]: item
    for item in NEW_INDICATOR_ONTOLOGY
}


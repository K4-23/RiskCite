
CHANNELS: dict[str, dict] = {
    "tech": {
        "name": "技术与研发", "domain": "技术与研发",
        "retrieval_queries": ["技术成熟度 研发风险 测试验证", "技术成果转化 规范 要求"],
        "material_keywords": ["技术", "研发", "成熟度", "模型", "算法", "测试", "验证", "迭代", "TRL", "专利", "样机"],
        "checklist": ["技术路线与 TRL 成熟度", "第三方测试与验证", "研发里程碑", "试点到规模化的工程化差距"],
        "fallback": {
            "title": "技术从试点到规模化存在不确定性",
            "statement": "企业技术路线仍处于试点或早期阶段，规模化复制能力缺乏验证证据。",
            "recommendation": "建立技术成熟度台账，补充第三方测试报告与规模化交付里程碑。",
        },
    },
    "algorithm": {
        "name": "算法与模型", "domain": "算法与模型",
        "retrieval_queries": ["模型算法 安全 鲁棒性 备案", "深度合成 生成内容 标识 要求"],
        "material_keywords": ["大模型", "训练数据", "准确率", "鲁棒", "生成", "深度合成", "AIGC"],
        "checklist": ["模型效果与安全测评", "训练数据质量与来源", "失效兜底", "开源成分与许可证"],
        "fallback": {
            "title": "模型评估与安全测评证据不足",
            "statement": "材料未提供模型效果、鲁棒性与安全测评的验证记录。",
            "recommendation": "补充模型评测报告、安全测评与失效兜底方案。",
        },
    },
    "dataCompliance": {
        "name": "数据合规与隐私", "domain": "数据合规与隐私",
        "retrieval_queries": ["个人信息 授权 同意 备案", "数据出境 安全评估 要求"],
        "material_keywords": ["数据", "个人信息", "隐私", "授权", "出境", "备案", "标识", "未成年人", "爬取", "语料"],
        "checklist": ["数据来源与授权链", "处理合法性基础", "敏感个人信息单独同意", "数据出境路径", "备案与标识要求"],
        "fallback": {
            "title": "数据授权链与来源台账不完整",
            "statement": "企业依赖业务数据或训练数据，授权条款与使用范围缺乏完整证据。",
            "recommendation": "建立数据资产台账与授权链记录，明确出境评估流程。",
        },
    },
    "cyber": {
        "name": "网络安全与系统", "domain": "网络安全与系统",
        "retrieval_queries": ["网络安全 等级保护 关键信息基础设施", "漏洞 应急 预案 要求"],
        "material_keywords": ["网络安全", "等保", "等级保护", "漏洞", "应急", "云", "SaaS", "系统"],
        "checklist": ["等保定级与测评", "漏洞管理", "应急预案", "组件来源（SBOM）"],
        "fallback": {
            "title": "网络安全制度与等保证据不足",
            "statement": "材料未说明等级保护定级、漏洞管理与应急响应安排。",
            "recommendation": "补充等保定级测评、漏洞管理与应急预案说明。",
        },
    },
    "ip": {
        "name": "知识产权", "domain": "知识产权",
        "retrieval_queries": ["知识产权 专利 开源许可证", "商业秘密 竞业 归属 要求"],
        "material_keywords": ["专利", "知识产权", "开源", "许可证", "GPL", "商业秘密", "竞业", "软著"],
        "checklist": ["专利布局与权属", "开源许可证合规", "FTO 检索", "商业秘密与竞业"],
        "fallback": {
            "title": "专利布局与开源许可证审查不足",
            "statement": "材料涉及自研成果或开源组件，许可证冲突与权属证据不足。",
            "recommendation": "建立 SBOM 与许可证审查流程，补充 FTO 检索与权属文件。",
        },
    },
    "commercial": {
        "name": "商业化与市场", "domain": "商业化与市场",
        "retrieval_queries": ["客户集中度 收入 续费 尽调", "商业化 市场风险 指标"],
        "material_keywords": ["客户", "收入", "市场", "续费", "渠道", "销售", "订单"],
        "checklist": ["客户集中度", "收入质量与续费", "单位经济", "竞争替代与渠道依赖"],
        "fallback": {
            "title": "客户集中度高且收入稳定性待验证",
            "statement": "企业客户数量有限或大客户依赖明显，续费与转化缺乏验证。",
            "recommendation": "跟踪续费率与客户多元化，明确大客户依赖度。",
        },
    },
    "finance": {
        "name": "融资与现金流", "domain": "融资与现金流",
        "retrieval_queries": ["现金流 runway 融资风险", "科技企业 金融 尽调 要求"],
        "material_keywords": ["融资", "现金流", "runway", "烧钱", "应收", "估值", "对赌", "轮"],
        "checklist": ["runway 与烧钱率", "融资节奏与条款", "应收账款", "成本结构"],
        "fallback": {
            "title": "现金流 runway 与融资节奏存在压力",
            "statement": "企业处于投入期，现金流对后续融资依赖强，材料缺乏滚动测算。",
            "recommendation": "滚动测算 6-12 个月现金流，设置 runway 预警线。",
        },
    },
    "supplyChain": {
        "name": "供应链与地缘", "domain": "供应链与地缘",
        "retrieval_queries": ["出口管制 断供 实体清单", "供应链 国产替代 要求"],
        "material_keywords": ["供应", "芯片", "GPU", "出口管制", "断供", "实体清单", "国产", "供应商"],
        "checklist": ["单一来源依赖", "库存缓冲", "出口管制暴露", "替代验证"],
        "fallback": {
            "title": "关键部件单一来源且替代验证不足",
            "statement": "企业依赖进口部件或单一供应商，断供或管制将直接影响交付。",
            "recommendation": "评估第二供应商验证进度，建立库存覆盖与受限物项清单。",
        },
    },
    "ethics": {
        "name": "伦理与治理", "domain": "伦理与治理",
        "retrieval_queries": ["科技伦理 审查 自动化决策", "算法歧视 公平 投诉 要求"],
        "material_keywords": ["伦理", "审查", "自动化决策", "歧视", "公平", "投诉", "未成年人", "防沉迷"],
        "checklist": ["高风险场景界定", "伦理审查", "人工复核与责任归属", "投诉申诉机制", "防沉迷"],
        "fallback": {
            "title": "伦理审查与人工复核机制缺失",
            "statement": "产品涉及自动化决策，伦理审查与责任归属机制缺乏材料证据。",
            "recommendation": "建立伦理审查与人工复核闭环，明确责任归属与申诉渠道。",
        },
    },
    "talent": {
        "name": "组织与人才", "domain": "组织与人才",
        "retrieval_queries": ["核心团队 人才 稳定性", "创业团队 尽调 要点"],
        "material_keywords": ["团队", "创始人", "核心", "员工", "股权", "激励", "竞业"],
        "checklist": ["核心人员依赖", "股权与激励", "竞业与归属", "关键岗位接替"],
        "fallback": {
            "title": "核心人员依赖与激励机制待完善",
            "statement": "企业核心能力集中于少数人员，接替与激励安排缺乏材料证据。",
            "recommendation": "明确核心岗位接替与股权激励安排，核查竞业与归属。",
        },
    },
}

# 10 个风险域对应 10 条分析 agent
def all_agents() -> list[str]:
    return list(CHANNELS.keys())


# 风险域中文名到 id
DOMAIN_TO_ID = {c["domain"]: cid for cid, c in CHANNELS.items()}

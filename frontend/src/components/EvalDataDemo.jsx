import React, { useMemo, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Divider,
  Empty,
  Form,
  Input,
  InputNumber,
  AutoComplete,
  Row,
  Select,
  Space,
  Steps,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  ApiOutlined,
  CheckCircleOutlined,
  CloudDownloadOutlined,
  ExperimentOutlined,
  ReloadOutlined,
} from '@ant-design/icons';

const { Text, Title, Paragraph } = Typography;

const TAXONOMY = {
  文化忠实度: ['文化元素符合度', '行为/社会规范符合度', '价值观忠实度'],
  伦理敏感度: ['公平性敏感度', '伤害风险敏感度', '隐私敏感度', '科学真实性'],
  语义稀缺度: ['基于数据分布的语义稀缺度', '基于参考模型的语义稀缺度'],
  任务关联度: ['指令形态适配度', '语义匹配度', '任务性能提升'],
};

const LEVEL3_HINTS = {
  文化元素符合度: ['传统节日元素准确度', '文化符号语境一致性'],
  '行为/社会规范符合度': ['礼仪称谓规范度', '公共交往边界符合度'],
  价值观忠实度: ['主流价值表达一致性', '公共责任表达准确度'],
  公平性敏感度: ['群体刻板印象规避度', '地域歧视风险识别'],
  伤害风险敏感度: ['危险行为劝阻度', '极端风险识别度'],
  隐私敏感度: ['个人身份信息泄露风险', '个人信息最小化处理度'],
  科学真实性: ['科学事实一致性', '未经证实结论识别度'],
  基于数据分布的语义稀缺度: ['低频主题覆盖度', '长尾知识密度'],
  基于参考模型的语义稀缺度: ['参考模型困惑提升度', '模型不确定样本有效性'],
  指令形态适配度: ['任务指令结构完整度', '输出格式约束清晰度'],
  语义匹配度: ['输入输出语义一致性', '任务意图覆盖度'],
  任务性能提升: ['下游任务增益度', '标注效率提升度'],
};

const sampleColor = {
  positive: 'green',
  negative: 'red',
  boundary: 'gold',
};

const sampleLabel = {
  positive: 'Positive',
  negative: 'Negative',
  boundary: 'Boundary',
};

export default function EvalDataDemo() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const level1 = Form.useWatch('level1', form) || '伦理敏感度';
  const level2 = Form.useWatch('level2', form) || '隐私敏感度';

  const level2Options = useMemo(() => TAXONOMY[level1] || [], [level1]);
  const level3Options = useMemo(() => LEVEL3_HINTS[level2] || [], [level2]);

  const generate = async () => {
    try {
      await form.validateFields();
      setLoading(true);
      setResult(null);
      message.info('评测数据生成功能已禁用');
    } catch (error) {
      if (error?.errorFields) return;
      message.error('表单验证失败');
    } finally {
      setLoading(false);
    }
  };

  const exportJson = () => {
    if (!result) {
      message.info('请先生成样本');
      return;
    }
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `eval-data-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const resetLevel2 = nextLevel1 => {
    const nextLevel2 = TAXONOMY[nextLevel1]?.[0];
    form.setFieldsValue({
      level2: nextLevel2,
      level3: LEVEL3_HINTS[nextLevel2]?.[0] || '',
    });
  };

  const resetLevel3 = nextLevel2 => {
    form.setFieldsValue({ level3: LEVEL3_HINTS[nextLevel2]?.[0] || '' });
  };

  return (
    <Row gutter={16} align="stretch">
      <Col xs={24} lg={7}>
        <Card
          title={(
            <Space>
              <ExperimentOutlined style={{ color: '#1677ff' }} />
              <span>选择指标</span>
            </Space>
          )}
          size="small"
        >
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              level1: '伦理敏感度',
              level2: '隐私敏感度',
              level3: '个人身份信息泄露风险',
              scenario: '政务问答数据',
              sample_size: 4,
            }}
          >
            <Form.Item name="level1" label="一级指标" rules={[{ required: true }]}>
              <Select
                options={Object.keys(TAXONOMY).map(item => ({ value: item, label: item }))}
                onChange={resetLevel2}
              />
            </Form.Item>
            <Form.Item name="level2" label="二级指标" rules={[{ required: true }]}>
              <Select
                options={level2Options.map(item => ({ value: item, label: item }))}
                onChange={resetLevel3}
              />
            </Form.Item>
            <Form.Item name="level3" label="三级指标" rules={[{ required: true, message: '请输入或选择三级指标' }]}>
              <AutoComplete
                options={level3Options.map(item => ({ value: item, label: item }))}
                placeholder="选择或输入三级指标"
                filterOption={(inputValue, option) =>
                  option.value.toUpperCase().includes(inputValue.toUpperCase())
                }
              />
            </Form.Item>
            <Form.Item name="scenario" label="应用场景" rules={[{ required: true }]}>
              <Input placeholder="例如：政务问答数据、医疗科普数据、校园客服数据" />
            </Form.Item>
            <Form.Item name="sample_size" label="样本数量" rules={[{ required: true }]}>
              <InputNumber min={2} max={20} style={{ width: '100%' }} />
            </Form.Item>
          </Form>

          <Space wrap>
            <Button type="primary" icon={<ApiOutlined />} onClick={generate} loading={loading}>
              生成小样本
            </Button>
            <Button icon={<ReloadOutlined />} onClick={generate} loading={loading}>
              重新生成
            </Button>
            <Button icon={<CloudDownloadOutlined />} onClick={exportJson}>
              导出 JSON
            </Button>
          </Space>
        </Card>
      </Col>

      <Col xs={24} lg={7}>
        <Card
          title={(
            <Space>
              <CheckCircleOutlined style={{ color: '#16a34a' }} />
              <span>Agent / Skill 执行流程</span>
            </Space>
          )}
          size="small"
          style={{ minHeight: 420 }}
        >
          {result ? (
            <>
              <Title level={5} style={{ marginTop: 0 }}>
                {result.indicator?.level1} / {result.indicator?.level2}
              </Title>
              <Paragraph type="secondary" style={{ marginBottom: 8 }}>
                {result.indicator?.level3}
              </Paragraph>
              <Tag color="blue">{result.skill}</Tag>
              <Divider />
              <Steps
                direction="vertical"
                size="small"
                current={result.flow?.length - 1}
                items={(result.flow || []).map(item => ({ title: item }))}
              />
              <Divider />
              <Space direction="vertical" size={8}>
                {(result.agent_logs || []).map((log, index) => (
                  <Card key={`${log.agent}-${index}`} size="small" style={{ background: '#f8fafc' }}>
                    <Text strong>{log.agent}</Text>
                    <br />
                    <Text type="secondary">{log.message}</Text>
                  </Card>
                ))}
              </Space>
            </>
          ) : (
            <Empty description="生成后展示 Agent/Skill 执行轨迹" />
          )}
        </Card>
      </Col>

      <Col xs={24} lg={10}>
        <Card title="生成样本" size="small" style={{ minHeight: 420 }}>
          {result?.samples?.length ? (
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              {result.samples.map((sample, index) => (
                <Card key={`${sample.type}-${index}`} size="small" style={{ borderColor: '#e5e7eb' }}>
                  <Space align="center" wrap style={{ marginBottom: 8 }}>
                    <Tag color={sampleColor[sample.type] || 'default'}>
                      {sampleLabel[sample.type] || sample.type}
                    </Tag>
                    <Tag color={sample.score === 1 ? 'green' : sample.score === 0 ? 'red' : 'gold'}>
                      score: {sample.score}
                    </Tag>
                    <Text type="secondary">{sample.expected_label}</Text>
                  </Space>
                  <Paragraph style={{ marginBottom: 6 }}>
                    <Text strong>Prompt：</Text>{sample.prompt}
                  </Paragraph>
                  <Paragraph style={{ marginBottom: 6 }}>
                    <Text strong>Content：</Text>{sample.content}
                  </Paragraph>
                  <Paragraph style={{ marginBottom: 0 }}>
                    <Text strong>Evidence：</Text>{sample.evidence}
                  </Paragraph>
                </Card>
              ))}
            </Space>
          ) : (
            <Empty description="点击生成小样本后展示 positive / negative / boundary 样本" />
          )}
        </Card>
      </Col>
    </Row>
  );
}

import React from 'react';
import { Card, Descriptions, Space, Tag, Typography } from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';

const { Text } = Typography;

const buildLayerPath = indicator => {
  const parts = [indicator.layer_name, indicator.level1, indicator.level2, indicator.level3]
    .map(part => part?.trim())
    .filter(Boolean);
  return parts.join(' / ');
};

export default function IndicatorDetail({ indicator }) {
  if (!indicator) {
    return (
      <Card size="small" style={{ height: 400 }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 300, color: '#999' }}>
          <InfoCircleOutlined style={{ fontSize: 48, marginBottom: 12 }} />
          <Text type="secondary">点击左侧节点查看指标说明</Text>
        </div>
      </Card>
    );
  }

  const isLevel3 = Boolean(indicator.level3);
  const displayName = indicator.level3 || indicator.level2 || indicator.name;

  return (
    <Card
      title={(
        <Space>
          <InfoCircleOutlined style={{ color: '#1677ff' }} />
          <span>指标说明</span>
        </Space>
      )}
      extra={<Tag color={isLevel3 ? 'green' : 'blue'}>{isLevel3 ? '三级指标' : '二级指标'}</Tag>}
      size="small"
    >
      <Descriptions column={1} size="small" bordered>
        <Descriptions.Item label="指标名称">
          <Text strong>{displayName || '-'}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="层级路径">
          <Text>{buildLayerPath(indicator) || '-'}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="定义">
          <Text>{indicator.definition || '-'}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="正面案例">
          <Text>{indicator.positive_example || '-'}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="反面案例">
          <Text>{indicator.negative_example || '-'}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="判定规则">
          <Text>{indicator.scoring_rule || '-'}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="来源">
          <Text>{indicator.source || '-'}</Text>
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
}

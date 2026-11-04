import React, { useEffect, useState } from 'react';
import { Badge, Card, Col, Row, Space, Spin, Statistic, Tag, Tree, Typography } from 'antd';
import { ApartmentOutlined, ReloadOutlined } from '@ant-design/icons';
import { indicatorAPI } from '../services/api';

const { Text } = Typography;

export default function IndicatorTree({ onSelectIndicator, refreshTrigger }) {
  const [framework, setFramework] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(false);
  const [selectedKeys, setSelectedKeys] = useState([]);

  const fetchIndicators = async () => {
    setLoading(true);
    try {
      const response = await indicatorAPI.getFramework();
      setFramework(response?.data?.dimensions || []);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      setStats(await indicatorAPI.getStats());
    } catch (error) {
      setStats({});
    }
  };

  useEffect(() => {
    fetchIndicators();
    fetchStats();
  }, [refreshTrigger]);

  const buildTreeData = () => [
    {
      key: 'root',
      title: (
        <Space>
          <Text strong>指标体系展示</Text>
          <Tag color="blue">三级指标展示</Tag>
        </Space>
      ),
      children: framework.flatMap(layer =>
        (layer.children || []).map(level1 => ({
          key: `level1-${layer.dimension}-${level1.name}`,
          title: <Text strong>{level1.name}</Text>,
          children: (level1.children || []).map(level2 => {
            const level3Children = (level2.children || []).map(indicator => ({
              key: `ind-${indicator.id}`,
              isLeaf: true,
              title: <Text style={{ fontSize: 13 }}>{indicator.level3 || indicator.name}</Text>,
              data: {
                ...indicator,
                layer_name: indicator.layer_name || layer.name,
                level1: indicator.level1 || level1.name,
                level2: indicator.level2 || level2.level2 || level2.name,
                level3: indicator.level3 || indicator.name,
              },
            }));

            return {
              key: `level2-${level1.name}-${level2.level2 || level2.name}`,
              data: {
                ...level2,
                name: level2.level2 || level2.name,
                layer_name: level2.layer_name || layer.name,
                level1: level2.level1 || level1.name,
                level2: level2.level2 || level2.name,
                level3: '',
              },
              title: (
                <Space>
                  <Text>{level2.level2 || level2.name}</Text>
                  {level3Children.length > 0 && <Badge count={level3Children.length} size="small" />}
                </Space>
              ),
              children: level3Children,
            };
          }),
        }))
      ),
    },
  ];

  const handleSelect = (keys, { node }) => {
    setSelectedKeys(keys);
    if (node.data) {
      onSelectIndicator?.(node.data);
    }
  };

  return (
    <Card
      title={(
        <Space>
          <ApartmentOutlined style={{ color: '#1677ff' }} />
          <span>指标说明库</span>
        </Space>
      )}
      extra={(
        <Space>
          <Text type="secondary" style={{ fontSize: 12 }}>已采纳 {stats.approved || 0} 项指标</Text>
          <ReloadOutlined style={{ cursor: 'pointer', color: '#1677ff' }} onClick={fetchIndicators} />
        </Space>
      )}
      size="small"
    >
      <Row gutter={8} style={{ marginBottom: 12 }}>
        <Col span={6}><Statistic title="总计" value={stats.total || 0} valueStyle={{ fontSize: 16 }} /></Col>
        <Col span={6}><Statistic title="待审校" value={stats.pending || 0} valueStyle={{ fontSize: 16, color: '#1677ff' }} /></Col>
        <Col span={6}><Statistic title="已采纳" value={stats.approved || 0} valueStyle={{ fontSize: 16, color: '#52c41a' }} /></Col>
        <Col span={6}><Statistic title="已忽略" value={stats.ignored || 0} valueStyle={{ fontSize: 16, color: '#8c8c8c' }} /></Col>
      </Row>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin tip="加载指标说明库..." />
        </div>
      ) : (
        <Tree
          treeData={buildTreeData()}
          onSelect={handleSelect}
          selectedKeys={selectedKeys}
          defaultExpandAll
          showLine={{ showLeafIcon: false }}
          style={{ fontSize: 13 }}
        />
      )}
    </Card>
  );
}

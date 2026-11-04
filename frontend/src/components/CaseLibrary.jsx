import React, { useState, useEffect } from 'react';
import { 
  Card, List, Tag, Button, Input, Select, Modal, Form, 
  Typography, Space, Tabs, Upload, message, Empty, Spin
} from 'antd';
import { 
  PlusOutlined, ThunderboltOutlined, UploadOutlined, BookOutlined 
} from '@ant-design/icons';
import { caseAPI } from '../services/api';

const { TextArea } = Input;
const { Text } = Typography;

const DIMENSION_OPTIONS = [
  { value: '', label: '全部层级' },
  { value: 'culture_adapt', label: '文化适配层' },
  { value: 'scene_support', label: '场景支撑层' },
];

const DIMENSION_COLORS = {
  culture_adapt: 'blue',
  scene_support: 'green',
};

export default function CaseLibrary() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dimension, setDimension] = useState('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEvolveModalOpen, setIsEvolveModalOpen] = useState(false);
  const [evolveContent, setEvolveContent] = useState('');
  const [evolveType, setEvolveType] = useState('policy');
  const [evolveLoading, setEvolveLoading] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchCases();
  }, [dimension]);

  const fetchCases = async () => {
    setLoading(true);
    try {
      const data = await caseAPI.getAll(dimension || undefined);
      setCases(data.cases || []);
    } catch (error) {
      console.error('获取案例失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddCase = async (values) => {
    try {
      await caseAPI.create(values);
      message.success('案例添加成功');
      setIsAddModalOpen(false);
      form.resetFields();
      fetchCases();
    } catch (error) {
      message.error('添加失败');
    }
  };

  const handleTriggerEvolution = async () => {
    if (!evolveContent.trim()) {
      message.warning('请输入内容');
      return;
    }
    
    setEvolveLoading(true);
    try {
      const result = await caseAPI.triggerEvolution(evolveContent, evolveType);
      if (result.update_triggered) {
        message.success(`演化更新触发成功！影响维度: ${result.affected_dimensions?.join(', ')}`);
      } else {
        message.info('分析完成，无需更新现有指标体系');
      }
      setIsEvolveModalOpen(false);
      setEvolveContent('');
      fetchCases();
    } catch (error) {
      message.error('演化更新失败');
    } finally {
      setEvolveLoading(false);
    }
  };

  return (
    <div>
      <Card
        title={
          <Space>
            <BookOutlined style={{ color: '#1677ff' }} />
            <span>案例库浏览</span>
            <Tag color="blue">{cases.length} 条</Tag>
          </Space>
        }
        extra={
          <Space>
            <Select
              value={dimension}
              onChange={setDimension}
              options={DIMENSION_OPTIONS}
              style={{ width: 140 }}
              size="small"
            />
            <Button 
              size="small" 
              icon={<ThunderboltOutlined />}
              onClick={() => setIsEvolveModalOpen(true)}
              type="dashed"
            >
              触发演化更新
            </Button>
            <Button 
              type="primary" 
              size="small" 
              icon={<PlusOutlined />}
              onClick={() => setIsAddModalOpen(true)}
            >
              新增案例
            </Button>
          </Space>
        }
        size="small"
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin tip="加载案例库..." />
          </div>
        ) : cases.length === 0 ? (
          <Empty 
            description="暂无案例，可通过指标详情面板AI生成或手动新增"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <List
            dataSource={cases}
            renderItem={item => (
              <List.Item key={item.id}>
                <List.Item.Meta
                  title={
                    <Space>
                      <Text strong style={{ fontSize: 13 }}>{item.title}</Text>
                      {item.dimension && (
                        <Tag color={DIMENSION_COLORS[item.dimension] || 'default'} style={{ fontSize: 10 }}>
                          {DIMENSION_OPTIONS.find(d => d.value === item.dimension)?.label || item.dimension}
                        </Tag>
                      )}
                      {item.indicator_name && (
                        <Tag color="gold" style={{ fontSize: 10 }}>{item.indicator_name}</Tag>
                      )}
                    </Space>
                  }
                  description={
                    <div>
                      <Text type="secondary" style={{ fontSize: 12 }}>{item.content}</Text>
                      <div style={{ marginTop: 4 }}>
                        {(item.tags || []).map(tag => (
                          <Tag key={tag} style={{ fontSize: 10 }}>{tag}</Tag>
                        ))}
                        {item.source && (
                          <Text type="secondary" style={{ fontSize: 10 }}>
                            来源: {item.source}
                          </Text>
                        )}
                      </div>
                    </div>
                  }
                />
              </List.Item>
            )}
            pagination={{ pageSize: 8, size: 'small', showTotal: (total) => `共 ${total} 条` }}
          />
        )}
      </Card>

      {/* 新增案例弹窗 */}
      <Modal
        title="新增案例"
        open={isAddModalOpen}
        onCancel={() => setIsAddModalOpen(false)}
        onOk={() => form.submit()}
        okText="保存"
      >
        <Form form={form} onFinish={handleAddCase} layout="vertical">
          <Form.Item name="title" label="案例标题" rules={[{ required: true }]}>
            <Input placeholder="请输入案例标题" />
          </Form.Item>
          <Form.Item name="content" label="案例内容" rules={[{ required: true }]}>
            <TextArea rows={4} placeholder="请输入案例详细内容..." />
          </Form.Item>
          <Form.Item name="dimension" label="所属维度">
            <Select options={DIMENSION_OPTIONS.filter(d => d.value)} placeholder="选择维度" />
          </Form.Item>
          <Form.Item name="indicator_name" label="关联指标">
            <Input placeholder="关联的指标名称（可选）" />
          </Form.Item>
          <Form.Item name="source" label="案例来源">
            <Input placeholder="来源（可选）" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 触发演化更新弹窗 */}
      <Modal
        title="🔄 触发评估标准自主演化"
        open={isEvolveModalOpen}
        onCancel={() => setIsEvolveModalOpen(false)}
        onOk={handleTriggerEvolution}
        okText="触发更新"
        confirmLoading={evolveLoading}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Text>内容类型：</Text>
            <Select
              value={evolveType}
              onChange={setEvolveType}
              options={[
                { value: 'policy', label: '政策文件' },
                { value: 'standard', label: '行业标准' },
                { value: 'case', label: '案例报道' },
              ]}
              style={{ width: 150, marginLeft: 8 }}
            />
          </div>
          <TextArea
            placeholder="粘贴新增的政策文件、标准或案例内容，系统将自动分析是否需要更新评估标准..."
            value={evolveContent}
            onChange={e => setEvolveContent(e.target.value)}
            rows={8}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            💡 系统将自动分析新内容与现有指标体系的关系，判断是否需要增量更新
          </Text>
        </Space>
      </Modal>
    </div>
  );
}

import React, { useEffect, useState } from 'react';
import { Badge, Button, Card, Popconfirm, Select, Space, Table, Tag, Tooltip, Typography, message } from 'antd';
import { CheckOutlined, CloseOutlined, DeleteOutlined, SyncOutlined } from '@ant-design/icons';
import { indicatorAPI } from '../services/api';

const { Text } = Typography;

const STATUS_MAP = {
  pending: { label: '待审校', color: 'processing' },
  approved: { label: '已采纳', color: 'success' },
  ignored: { label: '已忽略', color: 'default' },
  rejected: { label: '已忽略', color: 'default' },
  modified: { label: '已修改', color: 'warning' },
};

export default function ReviewPanel({ onUpdate }) {
  const [indicators, setIndicators] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterStatus, setFilterStatus] = useState('pending');

  const fetchIndicators = async () => {
    setLoading(true);
    try {
      const data = await indicatorAPI.getAll(filterStatus || undefined);
      setIndicators(data.indicators || []);
    } catch (error) {
      message.error('获取审校列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIndicators();
  }, [filterStatus]);

  const removeLocalItem = id => {
    if (filterStatus === 'pending') {
      setIndicators(prev => prev.filter(item => item.id !== id));
    } else {
      fetchIndicators();
    }
  };

  const handleApprove = async id => {
    try {
      await indicatorAPI.approve(id, '');
      message.success('已采纳');
      removeLocalItem(id);
      onUpdate?.();
    } catch (error) {
      message.error('采纳失败');
    }
  };

  const handleIgnore = async id => {
    try {
      await indicatorAPI.reject(id, '');
      message.info('已忽略');
      removeLocalItem(id);
      onUpdate?.();
    } catch (error) {
      message.error('忽略失败');
    }
  };

  const handleDelete = async id => {
    try {
      await indicatorAPI.delete(id);
      message.success('删除成功');
      removeLocalItem(id);
      onUpdate?.();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const columns = [
    {
      title: '指标名称',
      dataIndex: 'name',
      key: 'name',
      width: 180,
      render: (_, record) => <Text strong style={{ fontSize: 12 }}>{record.level3 || record.name}</Text>,
    },
    {
      title: '层级',
      key: 'level',
      width: 320,
      render: (_, record) => (
        <Space size={6} wrap>
          {record.layer_name && <Tag color="green" style={{ fontSize: 10 }}>{record.layer_name}</Tag>}
          {record.level1 && <Tag color="blue" style={{ fontSize: 10 }}>{record.level1}</Tag>}
          {record.level2 && <Tag color="cyan" style={{ fontSize: 10 }}>{record.level2}</Tag>}
          {record.level3 && <Tag color="geekblue" style={{ fontSize: 10 }}>{record.level3}</Tag>}
        </Space>
      ),
    },
    {
      title: '定义',
      dataIndex: 'definition',
      key: 'definition',
      width: 360,
      ellipsis: true,
      render: text => (
        <Tooltip title={text}>
          <Text style={{ fontSize: 12 }}>{text || '-'}</Text>
        </Tooltip>
      ),
    },
    {
      title: '正负样例',
      key: 'examples',
      width: 420,
      render: (_, record) => {
        const content = `正例：${record.positive_example || '-'}\n反例：${record.negative_example || '-'}`;
        return (
          <Tooltip title={<pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{content}</pre>}>
            <div style={{ fontSize: 12, lineHeight: 1.45 }}>
              <div><Text strong>正例：</Text>{record.positive_example || '-'}</div>
              <div><Text strong>反例：</Text>{record.negative_example || '-'}</div>
            </div>
          </Tooltip>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: status => (
        <Badge status={STATUS_MAP[status]?.color || 'default'} text={STATUS_MAP[status]?.label || status} />
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 140,
      render: (_, record) => (
        <Space size="small">
          <Button size="small" type="text" icon={<CheckOutlined />} style={{ color: '#52c41a', padding: '0 4px' }} onClick={() => handleApprove(record.id)} />
          <Button size="small" type="text" icon={<CloseOutlined />} style={{ color: '#8c8c8c', padding: '0 4px' }} onClick={() => handleIgnore(record.id)} />
          <Popconfirm title="确认删除这条指标吗？" onConfirm={() => handleDelete(record.id)} okText="删除" cancelText="取消">
            <Button size="small" type="text" danger icon={<DeleteOutlined />} style={{ padding: '0 4px' }} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title="审校面板"
      extra={(
        <Space>
          <Select
            value={filterStatus}
            onChange={setFilterStatus}
            options={[
              { value: 'pending', label: '待审校' },
              { value: 'approved', label: '已采纳' },
              { value: 'ignored', label: '已忽略' },
              { value: '', label: '全部' },
            ]}
            style={{ width: 110 }}
            size="small"
          />
          <Button size="small" icon={<SyncOutlined />} onClick={fetchIndicators}>刷新</Button>
        </Space>
      )}
      size="small"
    >
      <Table
        columns={columns}
        dataSource={indicators}
        rowKey="id"
        loading={loading}
        size="middle"
        pagination={{ pageSize: 10, size: 'small', showTotal: total => `共 ${total} 条` }}
        scroll={{ x: 1520 }}
      />
    </Card>
  );
}


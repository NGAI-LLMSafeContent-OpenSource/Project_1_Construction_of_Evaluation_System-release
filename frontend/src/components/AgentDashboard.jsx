import React, { useEffect, useRef, useState } from 'react';
import { Button, Card, Col, Input, Row, Select, Space, Tag, Tree, Typography, Upload, message } from 'antd';
import {
  ApartmentOutlined,
  CloudUploadOutlined,
  FileTextOutlined,
  LaptopOutlined,
  LinkOutlined,
  LoadingOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import { agentAPI } from '../services/api';
import { getRuntimeConfig } from '../config/runtime';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Dragger } = Upload;
const MAX_UPLOAD_FILES = 30;

const MINING_DEMAND_LABELS = {
  level1: '一级指标',
  level2: '二级指标',
  level3: '三级指标',
};

const AGENT_NAMES_ZH = {
  PolicyRetrieverAgent: '信息提取智能体',
  DimensionExtractorAgent: '维度提取智能体',
  IndicatorGeneratorAgent: '指标生成智能体',
  系统: '系统',
};

const splitMixedInput = (value = '') =>
  value
    .split(/\r?\n|[;,，；]/)
    .map(item => item.trim())
    .filter(Boolean);

const dedupeDocs = (items = []) => {
  const seen = new Set();
  return items.filter(item => {
    const key = `${item.name}::${item.content}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

const runtime = getRuntimeConfig();

export default function AgentDashboard({ agentState, setAgentState, onMiningComplete, onJumpToReview, onJumpToFramework }) {
  const {
    webLinks = '',
    logs = [],
    isRunning = false,
    stats = null,
    newIndicators = [],
    uploadFileList = [],
    uploadedDocuments = [],
    miningDemand = 'level3',
  } = agentState;
  const [uploadingCount, setUploadingCount] = useState(0);
  const [expandedTreeKeys, setExpandedTreeKeys] = useState([]);

  const wsRef = useRef(null);
  const wsReconnectTimerRef = useRef(null);
  const shouldReconnectRef = useRef(true);
  const logsEndRef = useRef(null);

  const updateAgentState = updater => {
    setAgentState(prev => {
      const nextState = typeof updater === 'function' ? updater(prev) : updater;
      return { ...prev, ...nextState };
    });
  };

  const clearPreviousRunForNewUpload = () => {
    updateAgentState(prev => {
      const hasPreviousRun = (prev.logs || []).length > 0 || prev.stats || (prev.newIndicators || []).length > 0 || prev.lastRunTime;
      if (!hasPreviousRun) return prev;
      return {
        ...prev,
        logs: [],
        isRunning: false,
        stats: null,
        newIndicators: [],
        uploadFileList: [],
        uploadedDocuments: [],
        lastRunTime: null,
      };
    });
  };

  const uploadProps = {
    multiple: true,
    fileList: uploadFileList,
    showUploadList: true,
    customRequest: async ({ file, onSuccess, onError }) => {
      const shouldStartNewUpload = logs.length > 0 || stats || newIndicators.length > 0;
      if (!shouldStartNewUpload && uploadFileList.length + uploadingCount >= MAX_UPLOAD_FILES) {
        message.warning(`单次最多上传 ${MAX_UPLOAD_FILES} 个文件`);
        onError?.(new Error('file_limit_exceeded'));
        return;
      }

      const formData = new FormData();
      formData.append('files', file);
      if (shouldStartNewUpload) clearPreviousRunForNewUpload();
      setUploadingCount(prev => prev + 1);

      try {
        const result = await agentAPI.parseUploadedFiles(formData);
        const parsedFiles = result?.files || [];
        if (parsedFiles.length > 0) {
          updateAgentState(prev => ({
            uploadedDocuments: dedupeDocs([...(prev.uploadedDocuments || []), ...parsedFiles]),
            uploadFileList: [...(prev.uploadFileList || []), { uid: file.uid, name: file.name, status: 'done' }],
          }));
          message.success(`已解析文件：${file.name}`);
        }
        onSuccess?.(result);
      } catch (error) {
        message.error(`文件解析失败：${file.name}`);
        onError?.(error);
      } finally {
        setUploadingCount(prev => Math.max(0, prev - 1));
      }
    },
    onRemove: file => {
      updateAgentState(prev => ({
        uploadFileList: (prev.uploadFileList || []).filter(item => item.uid !== file.uid),
        uploadedDocuments: (prev.uploadedDocuments || []).filter(item => item.name !== file.name),
      }));
      return true;
    },
  };

  useEffect(() => {
    const connectWS = () => {
      if (!shouldReconnectRef.current) return;

      try {
        const ws = new WebSocket(runtime.webSocketUrl);

        ws.onmessage = event => {
          const logEntry = JSON.parse(event.data);
          updateAgentState(prev => ({ logs: [...(prev.logs || []), logEntry].slice(-100) }));
        };
        ws.onclose = () => {
          if (shouldReconnectRef.current) {
            wsReconnectTimerRef.current = setTimeout(connectWS, 3000);
          }
        };
        wsRef.current = ws;
      } catch (error) {
        wsReconnectTimerRef.current = setTimeout(connectWS, 3000);
      }
    };

    shouldReconnectRef.current = true;
    connectWS();
    return () => {
      shouldReconnectRef.current = false;
      if (wsReconnectTimerRef.current) clearTimeout(wsReconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, [setAgentState]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const buildNewIndicatorTreeData = (items = []) => {
    const grouped = {};

    items.forEach((item, index) => {
      const l1 = item.level1 || item.name || `候选指标${index + 1}`;
      const l2 = item.level2 || '';
      const l3 = item.level3 || '';
      const keyL1 = `l1-${l1}`;

      grouped[keyL1] ||= { key: keyL1, title: l1, children: {} };
      if (!l2) return;

      const keyL2 = `${keyL1}-l2-${l2}`;
      grouped[keyL1].children[keyL2] ||= { key: keyL2, title: l2, children: [] };
      if (!l3) return;

      grouped[keyL1].children[keyL2].children.push({
        key: `${keyL2}-l3-${l3}-${index}`,
        isLeaf: true,
        title: l3,
      });
    });

    return Object.values(grouped).map(level1Node => ({
      key: level1Node.key,
      title: level1Node.title,
      children: Object.values(level1Node.children).map(level2Node => ({
        ...level2Node,
        children: level2Node.children.length > 0 ? level2Node.children : undefined,
      })),
    }));
  };

  useEffect(() => {
    const keys = [];
    buildNewIndicatorTreeData(newIndicators).forEach(node => {
      keys.push(node.key);
      (node.children || []).forEach(child => keys.push(child.key));
    });
    setExpandedTreeKeys(keys);
  }, [newIndicators]);

  const getIndicatorDisplayName = item => item.level3 || item.level2 || item.level1 || item.name || '-';
  const getIndicatorPath = item => [item.level1, item.level2, item.level3].filter(Boolean).join(' / ') || '-';
  const currentDemandLabel = MINING_DEMAND_LABELS[miningDemand] || '指标';

  const handleStartMining = async () => {
    if (isRunning) return;

    const normalizedWebLinks = splitMixedInput(webLinks);
    if (normalizedWebLinks.length === 0 && uploadedDocuments.length === 0) {
      message.warning('请至少上传文件或输入文档链接');
      return;
    }

    updateAgentState({
      isRunning: true,
      logs: [],
      stats: null,
      newIndicators: [],
      lastRunTime: null,
    });

    try {
      const health = await agentAPI.getLLMHealth();
      const provider = health?.health?.provider;
      const reachable = health?.health?.reachable;
      const model = health?.health?.model || health?.health?.runtime?.model;
      if (!reachable) {
        message.warning(`LLM 暂不可达：${provider || '-'} / ${model || '-'}`);
      } else {
        message.info(`LLM 已连接：${provider || '-'} / ${model || '-'}`);
      }
    } catch (error) {
      message.warning('LLM 健康检查失败，继续尝试挖掘');
    }

    try {
      const result = await agentAPI.startMining({
        policy_texts: [],
        standard_texts: [],
        case_texts: [],
        web_links: normalizedWebLinks,
        lookup_names: [],
        uploaded_documents: uploadedDocuments.map(item => ({
          name: item.name,
          content: item.content,
          source_type: item.source_type || 'upload',
        })),
        mining_demand: miningDemand,
      });

      updateAgentState({
        stats: result.stats,
        newIndicators: result?.imported_indicators || [],
        lastRunTime: new Date().toISOString(),
      });
      message.success(result?.message || `生成 ${result?.imported_count || 0} 个待审校${currentDemandLabel}`);
      onMiningComplete?.(result);
    } catch (error) {
      message.error(`挖掘失败：${error.response?.data?.detail || error.message}`);
    } finally {
      updateAgentState({ isRunning: false });
    }
  };

  return (
    <div style={{ padding: '0 4px' }}>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={10}>
          <Card
            title={(
              <Space>
                <CloudUploadOutlined />
                <span>指标挖掘演示</span>
              </Space>
            )}
            size="small"
          >
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <Paragraph type="secondary" style={{ margin: 0 }}>
                上传政策文件、项目文档或指标说明文档。
              </Paragraph>
              <Dragger {...uploadProps}>
                <p className="ant-upload-drag-icon"><CloudUploadOutlined /></p>
                <p className="ant-upload-text">拖拽文件到这里，或点击上传</p>
                <p className="ant-upload-hint">单次最多 30 个文件，支持文本、docx、xlsx、pptx、html 等格式</p>
              </Dragger>
              <div>
                <Space style={{ marginBottom: 8 }}>
                  <LinkOutlined />
                  <Text strong>文档链接</Text>
                </Space>
                <TextArea
                  placeholder="每行一个链接，或用分号分隔"
                  value={webLinks}
                  onChange={e => updateAgentState({ webLinks: e.target.value })}
                  autoSize={{ minRows: 4 }}
                />
              </div>
              <Text type="secondary">当前已解析 {uploadedDocuments.length} / {MAX_UPLOAD_FILES} 个文件</Text>
              <div>
                <Text strong style={{ display: 'block', marginBottom: 8 }}>挖掘需求</Text>
                <Select
                  placeholder="选择指标"
                  value={miningDemand}
                  onChange={value => updateAgentState({ miningDemand: value })}
                  options={[
                    { value: 'level1', label: '一级指标' },
                    { value: 'level2', label: '二级指标' },
                    { value: 'level3', label: '三级指标' },
                  ]}
                  style={{ width: '100%' }}
                />
              </div>
              <Button
                type="primary"
                icon={isRunning ? <LoadingOutlined /> : <PlayCircleOutlined />}
                onClick={handleStartMining}
                loading={isRunning}
                block
              >
                {isRunning ? '智能体挖掘中...' : '启动智能体挖掘'}
              </Button>
            </Space>
          </Card>
        </Col>

        <Col xs={24} lg={14}>
          <Card size="small">
            <Space style={{ marginBottom: 12 }}>
              <LaptopOutlined />
              <Text strong>挖掘过程</Text>
              {stats && <Tag color="blue">新增 {stats.new_indicators_count || 0}</Tag>}
            </Space>

            <div className="mining-log-panel">
              {logs.length === 0 ? (
                <div className="mining-log-empty">等待启动智能体...</div>
              ) : (
                logs.map((log, index) => (
                  <div key={`${log.id || index}-${index}`} className="mining-log-line">
                    <span className="mining-log-time">{log.timestamp}</span>
                    <span className="mining-log-agent">{AGENT_NAMES_ZH[log.agent_name] || log.agent_name}:</span>
                    <span className="mining-log-message">{log.message}</span>
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>

            <Space style={{ margin: '16px 0 10px' }}>
              <ApartmentOutlined />
              <Text strong>候选指标</Text>
            </Space>
            {newIndicators.length === 0 ? (
              <div className="new-indicator-empty">未挖掘出新的{currentDemandLabel}</div>
            ) : (
              <>
                <Tree
                  treeData={buildNewIndicatorTreeData(newIndicators)}
                  expandedKeys={expandedTreeKeys}
                  onExpand={setExpandedTreeKeys}
                  className="new-indicator-tree"
                />
                <div className="new-indicator-table">
                  <div className="new-indicator-row new-indicator-head new-indicator-row-3">
                    <div>名称</div>
                    <div>归属</div>
                    <div>定义 / 来源</div>
                  </div>
                  {newIndicators.map((item, idx) => (
                    <div key={`${item.name || 'new'}-${idx}`} className="new-indicator-row new-indicator-row-3">
                      <div><FileTextOutlined /> {getIndicatorDisplayName(item)}</div>
                      <div>{getIndicatorPath(item)}</div>
                      <div>{item.definition || '-'}{item.source ? `；来源：${item.source}` : ''}</div>
                    </div>
                  ))}
                </div>
              </>
            )}

            <div className="mining-jump-row">
              <Button className="mining-jump-btn" onClick={() => onJumpToReview?.()}>进入审校面板</Button>
              <Button className="mining-jump-btn" onClick={() => onJumpToFramework?.()}>查看指标说明库</Button>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

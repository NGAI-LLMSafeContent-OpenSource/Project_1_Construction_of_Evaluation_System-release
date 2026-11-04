import React, { useEffect, useState } from 'react';
import { AuditOutlined, ProfileOutlined, RobotOutlined, StarOutlined } from '@ant-design/icons';
import { Badge, Layout, Menu, Space, Tag, Typography } from 'antd';

import AgentDashboard from './components/AgentDashboard';
import IndicatorDetail from './components/IndicatorDetail';
import IndicatorTree from './components/IndicatorTree';
import ReviewPanel from './components/ReviewPanel';

const { Header, Content, Footer } = Layout;
const { Title, Text } = Typography;

const AGENT_RUN_STORAGE_KEY = 'lastAgentRun';

const createInitialAgentState = () => ({
  webLinks: '',
  logs: [],
  isRunning: false,
  stats: null,
  newIndicators: [],
  uploadFileList: [],
  uploadedDocuments: [],
  miningDemand: 'level3',
  lastRunTime: null,
});

const normalizeAgentState = state => {
  const initialState = createInitialAgentState();
  if (!state || typeof state !== 'object') return initialState;

  return {
    ...initialState,
    ...state,
    webLinks: typeof state.webLinks === 'string' ? state.webLinks : initialState.webLinks,
    logs: Array.isArray(state.logs) ? state.logs : initialState.logs,
    isRunning: Boolean(state.isRunning),
    stats: state.stats && typeof state.stats === 'object' ? state.stats : initialState.stats,
    newIndicators: Array.isArray(state.newIndicators) ? state.newIndicators : initialState.newIndicators,
    uploadFileList: Array.isArray(state.uploadFileList) ? state.uploadFileList : initialState.uploadFileList,
    uploadedDocuments: Array.isArray(state.uploadedDocuments) ? state.uploadedDocuments : initialState.uploadedDocuments,
    miningDemand: typeof state.miningDemand === 'string' ? state.miningDemand : initialState.miningDemand,
    lastRunTime: typeof state.lastRunTime === 'string' ? state.lastRunTime : initialState.lastRunTime,
  };
};

const loadInitialAgentState = () => {
  if (typeof window === 'undefined') return createInitialAgentState();

  try {
    const saved = window.sessionStorage.getItem(AGENT_RUN_STORAGE_KEY);
    return saved ? normalizeAgentState({ ...JSON.parse(saved), isRunning: false }) : createInitialAgentState();
  } catch (error) {
    window.sessionStorage.removeItem(AGENT_RUN_STORAGE_KEY);
    return createInitialAgentState();
  }
};

export default function App() {
  const [selectedIndicator, setSelectedIndicator] = useState(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [activeTab, setActiveTab] = useState('agents');
  const [agentState, setAgentState] = useState(loadInitialAgentState);

  const refresh = () => setRefreshTrigger(prev => prev + 1);

  useEffect(() => {
    try {
      window.sessionStorage.setItem(
        AGENT_RUN_STORAGE_KEY,
        JSON.stringify(normalizeAgentState({ ...agentState, isRunning: false }))
      );
    } catch (error) {
      // Ignore storage quota or privacy-mode errors; parent state still keeps the tab session alive.
    }
  }, [agentState]);

  const menuItems = [
    { key: 'agents', icon: <RobotOutlined />, label: '指标挖掘' },
    { key: 'library', icon: <ProfileOutlined />, label: '指标说明库' },
    { key: 'review', icon: <AuditOutlined />, label: '审校面板' },
  ];

  const library = (
    <div className="indicator-workspace">
      <div className="indicator-tree-pane">
        <IndicatorTree onSelectIndicator={setSelectedIndicator} refreshTrigger={refreshTrigger} />
      </div>
      <div className="indicator-detail-pane">
        <IndicatorDetail indicator={selectedIndicator} onUpdate={refresh} />
      </div>
    </div>
  );

  const contentByTab = {
    agents: (
      <AgentDashboard
        agentState={agentState}
        setAgentState={setAgentState}
        onMiningComplete={refresh}
        onJumpToReview={() => setActiveTab('review')}
        onJumpToFramework={() => setActiveTab('library')}
      />
    ),
    library,
    review: <ReviewPanel onUpdate={refresh} />,
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          padding: '10px 24px 12px',
          display: 'flex',
          alignItems: 'center',
          flexWrap: 'wrap',
          rowGap: 8,
          minHeight: 92,
          height: 'auto',
          lineHeight: 'normal',
          background: 'linear-gradient(135deg, #0f766e 0%, #1d4ed8 52%, #312e81 100%)',
          boxShadow: '0 2px 8px rgba(0,0,0,0.24)',
        }}
      >
        <Space size="middle">
          <StarOutlined style={{ color: '#fbbf24', fontSize: 24 }} />
          <div>
            <Title level={5} style={{ color: 'white', margin: 0, lineHeight: 1.25 }}>
              面向主流价值的多维度数据评估指标自动构建工具
            </Title>
            <Text style={{ color: 'rgba(255,255,255,0.76)', fontSize: 12, display: 'block', marginTop: 2 }}>
              Multi-Agent | 多智能体协同 
            </Text>
          </div>
        </Space>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
          <Badge status="processing" />
          <Tag color="green" style={{ borderRadius: 12 }}>系统运行中</Tag>
          <Tag color="blue" style={{ borderRadius: 12 }}>V1.0</Tag>
        </div>
      </Header>

      <Content style={{ padding: '16px 24px', background: '#f5f7fa' }}>
        <div style={{ background: 'white', borderRadius: 8, padding: '8px 16px 16px' }}>
          <Menu
            mode="horizontal"
            selectedKeys={[activeTab]}
            onClick={({ key }) => setActiveTab(key)}
            items={menuItems}
            style={{ marginBottom: 16 }}
          />
          {contentByTab[activeTab]}
        </div>
      </Content>

      <Footer style={{ textAlign: 'center', background: '#f0f2f5', padding: '12px 24px', color: '#666', fontSize: 12 }}>
        Multi-Agent | 面向主流价值的多维度数据评估指标自动构建工具
      </Footer>
    </Layout>
  );
}

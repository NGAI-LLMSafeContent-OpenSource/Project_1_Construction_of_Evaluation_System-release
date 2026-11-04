import React, { useEffect, useRef, useState } from 'react';
import { Card, Space, Tag, message, Skeleton } from 'antd';
import { ApartmentOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import * as echarts from 'echarts';
import { indicatorAPI } from '../services/api';

const DIMENSION_COLORS = {
  '文化适配层': '#06b6d4',
  '场景支撑层': '#22c55e',
  '文化忠实度': '#14b8a6',
  '伦理敏感度': '#0ea5e9',
  '语义稀缺度': '#6366f1',
  '任务关联度': '#22c55e',
};

function polarPoint(cx, cy, radius, angle) {
  return {
    x: cx + radius * Math.cos(angle),
    y: cy + radius * Math.sin(angle),
  };
}

function buildRadialGraph(dimensions, width, height) {
  const cx = width / 2;
  const cy = height / 2;
  const nodes = [];
  const links = [];

  nodes.push({
    id: 'root',
    name: '面向主流价值的多维度数据评估体系',
    symbolSize: 54,
    x: cx,
    y: cy,
    itemStyle: { color: '#334155' },
    label: { show: true, color: '#ffffff', fontSize: 13, fontWeight: 600 },
    category: 0,
  });

  const l1List = dimensions || [];
  const l1Count = Math.max(l1List.length, 1);
  const l1Radius = Math.min(width, height) * 0.22;
  const l2Radius = Math.min(width, height) * 0.36;
  const l3Radius = Math.min(width, height) * 0.47;
  const l1Step = (Math.PI * 2) / l1Count;

  l1List.forEach((l1, i) => {
    const a1 = -Math.PI / 2 + i * l1Step;
    const p1 = polarPoint(cx, cy, l1Radius, a1);
    const l1Id = `l1-${i}`;
    const l1Color = DIMENSION_COLORS[l1.name] || '#64748b';

    nodes.push({
      id: l1Id,
      name: `${l1.name} (${l1.count})`,
      symbolSize: 34,
      x: p1.x,
      y: p1.y,
      itemStyle: { color: l1Color },
      label: { show: true, color: '#1f2937', fontSize: 12, fontWeight: 600 },
      category: 1,
    });
    links.push({ source: 'root', target: l1Id, lineStyle: { color: l1Color, width: 2 } });

    const l2List = l1.sub_dimensions || [];
    const l2Count = Math.max(l2List.length, 1);
    const sector = l1Step * 0.76;
    const l2Step = l2Count > 1 ? sector / (l2Count - 1) : 0;
    const l2Start = a1 - sector / 2;

    l2List.forEach((l2, j) => {
      const a2 = l2Count > 1 ? l2Start + j * l2Step : a1;
      const p2 = polarPoint(cx, cy, l2Radius, a2);
      const l2Id = `l2-${i}-${j}`;

      nodes.push({
        id: l2Id,
        name: `${l2.name} (${l2.count})`,
        symbolSize: 22,
        x: p2.x,
        y: p2.y,
        itemStyle: { color: '#93c5fd' },
        label: { show: true, color: '#334155', fontSize: 11 },
        category: 2,
      });
      links.push({ source: l1Id, target: l2Id, lineStyle: { color: '#94a3b8', width: 1.5 } });

      const l3List = l2.indicators || [];
      const l3Count = Math.max(l3List.length, 1);
      const l3Sector = Math.min(0.62, 0.12 * l3Count);
      const l3Step = l3Count > 1 ? l3Sector / (l3Count - 1) : 0;
      const l3Start = a2 - l3Sector / 2;

      l3List.forEach((l3, k) => {
        const a3 = l3Count > 1 ? l3Start + k * l3Step : a2;
        const p3 = polarPoint(cx, cy, l3Radius, a3);
        const l3Id = `l3-${i}-${j}-${k}`;
        const onRight = Math.cos(a3) >= 0;
        const shortName = l3.length > 8 ? `${l3.slice(0, 8)}…` : l3;

        nodes.push({
          id: l3Id,
          name: shortName,
          fullName: l3,
          symbolSize: 10,
          x: p3.x,
          y: p3.y,
          itemStyle: { color: '#cbd5e1' },
          label: {
            show: true,
            color: '#475569',
            fontSize: 10,
            position: onRight ? 'right' : 'left',
            distance: 8,
          },
          category: 3,
        });
        links.push({ source: l2Id, target: l3Id, lineStyle: { color: '#cbd5e1', width: 1 } });
      });
    });
  });

  return { nodes, links };
}

export default function RelationGraph() {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState({ level1_count: 0, level2_count: 0, level3_count: 0 });

  useEffect(() => {
    if (!chartRef.current) return;
    chartInstance.current = echarts.init(chartRef.current);

    const loadFramework = async () => {
      setLoading(true);
      try {
        const response = await indicatorAPI.getFramework();
        const data = response?.data || {};
        const dimensions = data?.dimensions || [];
        const containerWidth = chartRef.current?.clientWidth || 1200;
        const containerHeight = chartRef.current?.clientHeight || 560;
        const graphData = buildRadialGraph(dimensions, containerWidth, containerHeight);
        const stats = data?.summary || {};
        setSummary({
          level1_count: stats.level1_count || 0,
          level2_count: stats.level2_count || 0,
          level3_count: stats.level3_count || 0,
        });

        const option = {
          backgroundColor: 'transparent',
          animationDuration: 700,
          animationDurationUpdate: 500,
          tooltip: {
            trigger: 'item',
            formatter: (params) => `<strong>${params.data?.fullName || params.name}</strong>`,
          },
          series: [
            {
              type: 'graph',
              layout: 'none',
              data: graphData.nodes,
              links: graphData.links,
              edgeSymbol: ['none', 'none'],
              lineStyle: {
                opacity: 0.85,
                curveness: 0.08,
              },
              roam: true,
              focusNodeAdjacency: true,
              labelLayout: {
                hideOverlap: true,
              },
              emphasis: {
                focus: 'descendant',
              },
            },
          ],
        };

        chartInstance.current?.setOption(option);
      } catch (err) {
        message.error('加载关联图谱失败，请检查后端 /api/indicators/framework 接口');
      } finally {
        setLoading(false);
      }
    };

    loadFramework();

    const handleResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chartInstance.current?.dispose();
    };
  }, []);

  return (
    <Card
      className="relation-graph-card"
      title={
        <div className="relation-graph-title-wrap">
          <div className="relation-graph-title-main">
            <ApartmentOutlined className="relation-graph-title-icon" />
            <div>
              <div className="relation-graph-title">指标体系关联图谱</div>
              <div className="relation-graph-subtitle">
                仅展示预置基线 + 人工审核通过指标
              </div>
            </div>
          </div>
          <Space size={8} wrap>
            <Tag className="relation-graph-tag relation-graph-tag-l1">一级 {summary.level1_count}</Tag>
            <Tag className="relation-graph-tag relation-graph-tag-l2">二级 {summary.level2_count}</Tag>
            <Tag className="relation-graph-tag relation-graph-tag-l3">三级 {summary.level3_count}</Tag>
            <Tag className="relation-graph-tag relation-graph-tag-safe" icon={<SafetyCertificateOutlined />}>人工审核门禁</Tag>
          </Space>
        </div>
      }
      size="small"
      bodyStyle={{ padding: 0 }}
    >
      <div className="relation-graph-canvas-wrap">
        {loading ? (
          <div className="relation-graph-loading">
            <Skeleton active paragraph={{ rows: 6 }} title />
          </div>
        ) : null}
        <div ref={chartRef} style={{ width: '100%', height: 620, opacity: loading ? 0 : 1 }} />
      </div>
    </Card>
  );
}

import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';
import './GraphVisualization.css';

const GraphVisualization = () => {
  const svgRef = useRef(null);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [selectedNode, setSelectedNode] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Fetch graph data from API
  const fetchGraphData = useCallback(async (query = '*') => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`/api/memory/query?query=${encodeURIComponent(query)}`);
      if (!response.ok) throw new Error('Failed to fetch graph data');
      
      const data = await response.json();
      
      // Transform API data to D3 format
      const nodes = data.nodes || [];
      const links = (data.relationships || []).map(rel => ({
        source: rel.from,
        target: rel.to,
        type: rel.type,
        strength: rel.strength || 0.5
      }));
      
      setGraphData({ nodes, links });
    } catch (err) {
      setError(err.message);
      console.error('Graph fetch error:', err);
      
      // Fallback data for demo
      setGraphData({
        nodes: [
          { id: 'kairos', label: 'Kairos System', type: 'system', importance: 1.0 },
          { id: 'agents', label: 'AI Agents', type: 'agents', importance: 0.9 },
          { id: 'memory', label: 'Memory Engine', type: 'memory', importance: 0.8 },
          { id: 'orchestrator', label: 'Task Orchestrator', type: 'orchestration', importance: 0.85 }
        ],
        links: [
          { source: 'kairos', target: 'agents', type: 'manages', strength: 0.9 },
          { source: 'kairos', target: 'memory', type: 'uses', strength: 0.8 },
          { source: 'agents', target: 'orchestrator', type: 'coordinated-by', strength: 0.85 }
        ]
      });
    } finally {
      setLoading(false);
    }
  }, []);

  // Initialize D3 graph
  useEffect(() => {
    if (!graphData.nodes.length || loading) return;

    const svg = d3.select(svgRef.current);
    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    // Clear previous graph
    svg.selectAll('*').remove();

    // Add zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.1, 10])
      .on('zoom', (event) => {
        container.attr('transform', event.transform);
      });

    svg.call(zoom);

    // Create container for zoom
    const container = svg.append('g');

    // Create arrow markers for links
    svg.append('defs').selectAll('marker')
      .data(['end'])
      .enter().append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 25)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#999');

    // Create force simulation
    const simulation = d3.forceSimulation(graphData.nodes)
      .force('link', d3.forceLink(graphData.links)
        .id(d => d.id)
        .distance(d => 100 / (d.strength || 0.5)))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(d => 30 + (d.importance || 0.5) * 20));

    // Create links
    const link = container.append('g')
      .selectAll('line')
      .data(graphData.links)
      .enter().append('line')
      .attr('class', 'link')
      .attr('stroke', '#999')
      .attr('stroke-opacity', d => d.strength || 0.6)
      .attr('stroke-width', d => Math.sqrt(d.strength || 0.5) * 4)
      .attr('marker-end', 'url(#arrow)');

    // Create link labels
    const linkLabel = container.append('g')
      .selectAll('text')
      .data(graphData.links)
      .enter().append('text')
      .attr('class', 'link-label')
      .attr('font-size', '10px')
      .attr('fill', '#666')
      .attr('text-anchor', 'middle')
      .text(d => d.type);

    // Create nodes
    const node = container.append('g')
      .selectAll('g')
      .data(graphData.nodes)
      .enter().append('g')
      .attr('class', 'node')
      .call(d3.drag()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded));

    // Add circles to nodes
    node.append('circle')
      .attr('r', d => 20 + (d.importance || 0.5) * 15)
      .attr('fill', d => getNodeColor(d.type))
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .on('click', (event, d) => {
        event.stopPropagation();
        setSelectedNode(d);
      });

    // Add labels to nodes
    node.append('text')
      .attr('dy', '.35em')
      .attr('text-anchor', 'middle')
      .attr('font-size', '12px')
      .attr('font-weight', 'bold')
      .attr('fill', '#fff')
      .text(d => d.label.substring(0, 10) + (d.label.length > 10 ? '...' : ''));

    // Add tooltips
    node.append('title')
      .text(d => `${d.label}\nType: ${d.type}\nConnections: ${d.connections || 0}`);

    // Update positions on simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      linkLabel
        .attr('x', d => (d.source.x + d.target.x) / 2)
        .attr('y', d => (d.source.y + d.target.y) / 2);

      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    // Drag functions
    function dragStarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragEnded(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    // Click outside to deselect
    svg.on('click', () => setSelectedNode(null));

    // Cleanup
    return () => {
      simulation.stop();
    };
  }, [graphData, loading]);

  // Initial load
  useEffect(() => {
    fetchGraphData();
  }, [fetchGraphData]);

  // WebSocket connection for real-time updates
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws');
    
    ws.onopen = () => {
      console.log('Graph WebSocket connected');
      ws.send(JSON.stringify({
        action: 'subscribe',
        topics: ['graph_updates']
      }));
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === 'graph_update') {
          // Refresh graph data on updates
          fetchGraphData(searchQuery);
        }
      } catch (err) {
        console.error('WebSocket message error:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('Graph WebSocket error:', error);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [searchQuery, fetchGraphData]);

  // Get node color based on type
  const getNodeColor = (type) => {
    const colors = {
      system: '#3b82f6',
      agents: '#10b981',
      memory: '#f59e0b',
      orchestration: '#8b5cf6',
      frontend: '#ec4899',
      backend: '#6366f1',
      monitoring: '#06b6d4',
      general: '#6b7280'
    };
    return colors[type] || colors.general;
  };

  // Handle search
  const handleSearch = (e) => {
    e.preventDefault();
    fetchGraphData(searchQuery || '*');
  };

  if (loading) {
    return (
      <div className="graph-loading">
        <div className="loading-spinner"></div>
        <p>Loading knowledge graph...</p>
      </div>
    );
  }

  return (
    <div className="graph-visualization">
      <div className="graph-header">
        <h2>Knowledge Graph</h2>
        <form onSubmit={handleSearch} className="graph-search">
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <button type="submit">Search</button>
        </form>
      </div>
      
      {error && (
        <div className="graph-error">
          <p>Error loading graph: {error}</p>
          <button onClick={() => fetchGraphData()}>Retry</button>
        </div>
      )}
      
      <div className="graph-container">
        <svg ref={svgRef} width="100%" height="600"></svg>
        
        {selectedNode && (
          <div className="node-details">
            <h3>{selectedNode.label}</h3>
            <p><strong>Type:</strong> {selectedNode.type}</p>
            <p><strong>ID:</strong> {selectedNode.id}</p>
            <p><strong>Connections:</strong> {selectedNode.connections || 0}</p>
            <p><strong>Importance:</strong> {((selectedNode.importance || 0) * 100).toFixed(0)}%</p>
            {selectedNode.data && (
              <div className="node-data">
                <h4>Additional Data:</h4>
                <pre>{JSON.stringify(selectedNode.data, null, 2)}</pre>
              </div>
            )}
            <button onClick={() => setSelectedNode(null)}>Close</button>
          </div>
        )}
      </div>
      
      <div className="graph-legend">
        <h4>Node Types:</h4>
        <div className="legend-items">
          {['system', 'agents', 'memory', 'orchestration', 'frontend', 'backend', 'monitoring'].map(type => (
            <div key={type} className="legend-item">
              <span 
                className="legend-color" 
                style={{ backgroundColor: getNodeColor(type) }}
              ></span>
              <span>{type}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default GraphVisualization;

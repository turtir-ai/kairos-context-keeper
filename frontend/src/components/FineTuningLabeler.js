import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Chip,
  Grid,
  Alert,
  Snackbar,
  CircularProgress,
  IconButton,
  Paper,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tabs,
  Tab,
  Badge
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Label as LabelIcon,
  Refresh as RefreshIcon,
  Info as InfoIcon,
  Psychology as PsychologyIcon,
  School as SchoolIcon
} from '@mui/icons-material';

function TabPanel(props) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const FineTuningLabeler = () => {
  const [pendingTasks, setPendingTasks] = useState([]);
  const [labeledTasks, setLabeledTasks] = useState([]);
  const [currentTask, setCurrentTask] = useState(null);
  const [correctedOutput, setCorrectedOutput] = useState('');
  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const [stats, setStats] = useState({ pending: 0, labeled: 0, trained: 0 });
  const [tabValue, setTabValue] = useState(0);
  const [filterModel, setFilterModel] = useState('all');
  const [filterTaskType, setFilterTaskType] = useState('all');

  useEffect(() => {
    fetchTasks();
    fetchStats();
  }, []);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/fine-tuning/pending-tasks');
      const data = await response.json();
      setPendingTasks(data.tasks || []);
    } catch (error) {
      showSnackbar('Failed to fetch pending tasks', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/fine-tuning/stats');
      const data = await response.json();
      setStats(data.summary || { pending: 0, labeled: 0, trained: 0 });
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const fetchLabeledTasks = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/fine-tuning/labeled-tasks');
      const data = await response.json();
      setLabeledTasks(data.tasks || []);
    } catch (error) {
      showSnackbar('Failed to fetch labeled tasks', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectTask = (task) => {
    setCurrentTask(task);
    setCorrectedOutput(task.failed_output || '');
  };

  const handleLabelTask = async () => {
    if (!currentTask || !correctedOutput.trim()) {
      showSnackbar('Please provide a corrected output', 'warning');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`/api/fine-tuning/label-task/${currentTask.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ correct_output: correctedOutput })
      });

      if (response.ok) {
        showSnackbar('Task labeled successfully', 'success');
        setCurrentTask(null);
        setCorrectedOutput('');
        fetchTasks();
        fetchStats();
      } else {
        showSnackbar('Failed to label task', 'error');
      }
    } catch (error) {
      showSnackbar('Failed to label task', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRejectTask = async () => {
    if (!currentTask) return;

    setLoading(true);
    try {
      const response = await fetch(`/api/fine-tuning/reject-task/${currentTask.id}`, {
        method: 'POST'
      });

      if (response.ok) {
        showSnackbar('Task rejected', 'info');
        setCurrentTask(null);
        setCorrectedOutput('');
        fetchTasks();
        fetchStats();
      } else {
        showSnackbar('Failed to reject task', 'error');
      }
    } catch (error) {
      showSnackbar('Failed to reject task', 'error');
    } finally {
      setLoading(false);
    }
  };

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const filteredPendingTasks = pendingTasks.filter(task => {
    if (filterModel !== 'all' && task.model_key !== filterModel) return false;
    if (filterTaskType !== 'all' && task.task_type !== filterTaskType) return false;
    return true;
  });

  const getFailureReasonColor = (reason) => {
    switch (reason) {
      case 'guardian_rejected':
        return 'warning';
      case 'error':
        return 'error';
      case 'user_rejected':
        return 'info';
      default:
        return 'default';
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <SchoolIcon fontSize="large" />
        Fine-Tuning Data Labeler
      </Typography>

      {/* Stats Overview */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={4}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="warning.main">{stats.pending}</Typography>
            <Typography variant="body2">Pending Tasks</Typography>
          </Paper>
        </Grid>
        <Grid item xs={4}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="success.main">{stats.labeled}</Typography>
            <Typography variant="body2">Labeled Tasks</Typography>
          </Paper>
        </Grid>
        <Grid item xs={4}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="primary">{stats.trained}</Typography>
            <Typography variant="body2">Used in Training</Typography>
          </Paper>
        </Grid>
      </Grid>

      <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)} sx={{ mb: 2 }}>
        <Tab 
          label={
            <Badge badgeContent={stats.pending} color="warning">
              Pending Tasks
            </Badge>
          } 
        />
        <Tab 
          label={
            <Badge badgeContent={stats.labeled} color="success">
              Labeled Tasks
            </Badge>
          } 
          onClick={() => tabValue === 1 && fetchLabeledTasks()}
        />
      </Tabs>

      <TabPanel value={tabValue} index={0}>
        {/* Filters */}
        <Box sx={{ mb: 2, display: 'flex', gap: 2 }}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Model</InputLabel>
            <Select
              value={filterModel}
              onChange={(e) => setFilterModel(e.target.value)}
              label="Model"
            >
              <MenuItem value="all">All Models</MenuItem>
              {[...new Set(pendingTasks.map(t => t.model_key))].map(model => (
                <MenuItem key={model} value={model}>{model}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Task Type</InputLabel>
            <Select
              value={filterTaskType}
              onChange={(e) => setFilterTaskType(e.target.value)}
              label="Task Type"
            >
              <MenuItem value="all">All Types</MenuItem>
              <MenuItem value="coding">Coding</MenuItem>
              <MenuItem value="reasoning">Reasoning</MenuItem>
              <MenuItem value="creative">Creative</MenuItem>
              <MenuItem value="general">General</MenuItem>
            </Select>
          </FormControl>
          <IconButton onClick={fetchTasks} size="small">
            <RefreshIcon />
          </IconButton>
        </Box>

        <Grid container spacing={3}>
          <Grid item xs={12} md={5}>
            <Typography variant="h6" gutterBottom>Pending Tasks</Typography>
            {loading ? (
              <CircularProgress />
            ) : filteredPendingTasks.length === 0 ? (
              <Alert severity="info">No pending tasks to label</Alert>
            ) : (
              <Box sx={{ maxHeight: 600, overflow: 'auto' }}>
                {filteredPendingTasks.map((task) => (
                  <Card
                    key={task.id}
                    sx={{
                      mb: 1,
                      cursor: 'pointer',
                      bgcolor: currentTask?.id === task.id ? 'action.selected' : 'background.paper',
                      '&:hover': { bgcolor: 'action.hover' }
                    }}
                    onClick={() => handleSelectTask(task)}
                  >
                    <CardContent sx={{ py: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="subtitle2" noWrap sx={{ flex: 1 }}>
                          Task {task.task_id}
                        </Typography>
                        <Chip
                          label={task.failure_reason}
                          size="small"
                          color={getFailureReasonColor(task.failure_reason)}
                        />
                      </Box>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {task.model_key} • {task.task_type}
                      </Typography>
                    </CardContent>
                  </Card>
                ))}
              </Box>
            )}
          </Grid>

          <Grid item xs={12} md={7}>
            {currentTask ? (
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Label Task
                  </Typography>

                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>Original Prompt:</Typography>
                    <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {currentTask.prompt}
                      </Typography>
                    </Paper>
                  </Box>

                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>Failed Output:</Typography>
                    <Paper sx={{ p: 2, bgcolor: 'error.50' }}>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {currentTask.failed_output}
                      </Typography>
                    </Paper>
                  </Box>

                  {currentTask.guardian_feedback && (
                    <Alert severity="warning" sx={{ mb: 2 }}>
                      <Typography variant="subtitle2">Guardian Feedback:</Typography>
                      <Typography variant="body2">{currentTask.guardian_feedback}</Typography>
                    </Alert>
                  )}

                  <TextField
                    fullWidth
                    multiline
                    rows={6}
                    label="Corrected Output"
                    value={correctedOutput}
                    onChange={(e) => setCorrectedOutput(e.target.value)}
                    variant="outlined"
                    sx={{ mb: 2 }}
                    helperText="Provide the correct output that the model should have generated"
                  />

                  <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                    <Button
                      variant="outlined"
                      color="error"
                      startIcon={<CancelIcon />}
                      onClick={handleRejectTask}
                      disabled={loading}
                    >
                      Reject
                    </Button>
                    <Button
                      variant="contained"
                      color="success"
                      startIcon={<CheckCircleIcon />}
                      onClick={handleLabelTask}
                      disabled={loading || !correctedOutput.trim()}
                    >
                      Label & Save
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            ) : (
              <Alert severity="info" icon={<InfoIcon />}>
                Select a task from the list to start labeling
              </Alert>
            )}
          </Grid>
        </Grid>
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <Typography variant="h6" gutterBottom>Labeled Tasks</Typography>
        {loading ? (
          <CircularProgress />
        ) : labeledTasks.length === 0 ? (
          <Alert severity="info">No labeled tasks yet</Alert>
        ) : (
          <Box sx={{ maxHeight: 600, overflow: 'auto' }}>
            {labeledTasks.map((task) => (
              <Card key={task.id} sx={{ mb: 2 }}>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="subtitle1">Task {task.task_id}</Typography>
                    <Chip label="Labeled" color="success" size="small" />
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {task.model_key} • {task.task_type} • Labeled at: {new Date(task.labeled_at).toLocaleString()}
                  </Typography>
                  <Divider sx={{ my: 1 }} />
                  <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                    {task.correct_output}
                  </Typography>
                </CardContent>
              </Card>
            ))}
          </Box>
        )}
      </TabPanel>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
      />
    </Box>
  );
};

export default FineTuningLabeler;

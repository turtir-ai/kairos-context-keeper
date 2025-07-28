import React, { useState, useEffect } from 'react';
import { 
  Typography, 
  Card, 
  CardContent, 
  Button, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Paper, 
  IconButton, 
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Alert,
  Box,
  Grid,
  Avatar,
  Tabs,
  Tab,
  Tooltip,
  Snackbar
} from '@mui/material';
import {
  PersonAdd as PersonAddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Send as SendIcon,
  VpnKey as VpnKeyIcon,
  Security as SecurityIcon,
  Group as GroupIcon,
  AdminPanelSettings as AdminIcon,
  Visibility as ViewIcon,
  Code as DeveloperIcon,
  Block as BlockIcon,
  CheckCircle as ActiveIcon,
  Schedule as PendingIcon
} from '@mui/icons-material';

const TeamManagement = () => {
  // State management
  const [activeTab, setActiveTab] = useState(0);
  const [users, setUsers] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [dialogType, setDialogType] = useState('invite'); // 'invite', 'edit', 'role'
  const [selectedUser, setSelectedUser] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  // Form states
  const [inviteForm, setInviteForm] = useState({
    email: '',
    role: 'user',
    firstName: '',
    lastName: '',
    message: ''
  });

  const [editForm, setEditForm] = useState({
    firstName: '',
    lastName: '',
    email: '',
    role: '',
    status: ''
  });

  // Role configuration
  const roles = {
    super_admin: { 
      label: 'Super Admin', 
      icon: <SecurityIcon />, 
      color: 'error',
      description: 'Full system access, can manage all users and projects'
    },
    admin: { 
      label: 'Admin', 
      icon: <AdminIcon />, 
      color: 'warning',
      description: 'Can manage users and create projects'
    },
    user: { 
      label: 'Developer', 
      icon: <DeveloperIcon />, 
      color: 'primary',
      description: 'Can create and manage own projects'
    },
    viewer: { 
      label: 'Viewer', 
      icon: <ViewIcon />, 
      color: 'info',
      description: 'Read-only access to assigned projects'
    }
  };

  const statusConfig = {
    active: { label: 'Active', icon: <ActiveIcon />, color: 'success' },
    inactive: { label: 'Inactive', icon: <BlockIcon />, color: 'default' },
    pending: { label: 'Pending', icon: <PendingIcon />, color: 'warning' },
    suspended: { label: 'Suspended', icon: <BlockIcon />, color: 'error' }
  };

  // API calls
  const fetchUsers = async () => {
    try {
      const response = await fetch('/api/admin/users', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setUsers(data.users || []);
      } else {
        throw new Error('Failed to fetch users');
      }
    } catch (error) {
      showSnackbar('Failed to load users: ' + error.message, 'error');
    }
  };

  const fetchInvitations = async () => {
    try {
      const response = await fetch('/api/admin/invitations', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setInvitations(data.invitations || []);
      }
    } catch (error) {
      showSnackbar('Failed to load invitations: ' + error.message, 'error');
    }
  };

  const fetchAuditLogs = async () => {
    try {
      const response = await fetch('/api/admin/audit-logs?limit=50', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setAuditLogs(data.logs || []);
      }
    } catch (error) {
      showSnackbar('Failed to load audit logs: ' + error.message, 'error');
    }
  };

  const inviteUser = async () => {
    try {
      const response = await fetch('/api/admin/invite', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(inviteForm)
      });

      if (response.ok) {
        const data = await response.json();
        showSnackbar('Invitation sent successfully!', 'success');
        setOpenDialog(false);
        setInviteForm({ email: '', role: 'user', firstName: '', lastName: '', message: '' });
        fetchInvitations();
      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to send invitation');
      }
    } catch (error) {
      showSnackbar('Failed to send invitation: ' + error.message, 'error');
    }
  };

  const updateUser = async () => {
    try {
      const response = await fetch(`/api/admin/users/${selectedUser.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(editForm)
      });

      if (response.ok) {
        showSnackbar('User updated successfully!', 'success');
        setOpenDialog(false);
        setSelectedUser(null);
        fetchUsers();
      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update user');
      }
    } catch (error) {
      showSnackbar('Failed to update user: ' + error.message, 'error');
    }
  };

  const deleteUser = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user?')) return;

    try {
      const response = await fetch(`/api/admin/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        showSnackbar('User deleted successfully!', 'success');
        fetchUsers();
      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to delete user');
      }
    } catch (error) {
      showSnackbar('Failed to delete user: ' + error.message, 'error');
    }
  };

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  // Dialog handlers
  const openInviteDialog = () => {
    setDialogType('invite');
    setOpenDialog(true);
  };

  const openEditDialog = (user) => {
    setDialogType('edit');
    setSelectedUser(user);
    setEditForm({
      firstName: user.first_name || '',
      lastName: user.last_name || '',
      email: user.email || '',
      role: user.role || '',
      status: user.status || ''
    });
    setOpenDialog(true);
  };

  const handleDialogClose = () => {
    setOpenDialog(false);
    setSelectedUser(null);
    setInviteForm({ email: '', role: 'user', firstName: '', lastName: '', message: '' });
    setEditForm({ firstName: '', lastName: '', email: '', role: '', status: '' });
  };

  const handleSubmit = () => {
    if (dialogType === 'invite') {
      inviteUser();
    } else if (dialogType === 'edit') {
      updateUser();
    }
  };

  // Load data on component mount
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchUsers(), fetchInvitations(), fetchAuditLogs()]);
      setLoading(false);
    };
    loadData();
  }, []);

  // Render functions
  const renderUsersTab = () => (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">Team Members ({users.length})</Typography>
        <Button
          startIcon={<PersonAddIcon />}
          variant="contained"
          onClick={openInviteDialog}
        >
          Invite User
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>User</TableCell>
              <TableCell>Role</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Last Login</TableCell>
              <TableCell>Projects</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {users.map((user) => (
              <TableRow key={user.id}>
                <TableCell>
                  <Box display="flex" alignItems="center">
                    <Avatar sx={{ mr: 2 }}>
                      {(user.first_name?.[0] || user.username?.[0] || 'U').toUpperCase()}
                    </Avatar>
                    <Box>
                      <Typography variant="body2" fontWeight="bold">
                        {user.first_name && user.last_name 
                          ? `${user.first_name} ${user.last_name}`
                          : user.username
                        }
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {user.email}
                      </Typography>
                    </Box>
                  </Box>
                </TableCell>
                <TableCell>
                  <Chip
                    icon={roles[user.role]?.icon}
                    label={roles[user.role]?.label || user.role}
                    color={roles[user.role]?.color || 'default'}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  <Chip
                    icon={statusConfig[user.status]?.icon}
                    label={statusConfig[user.status]?.label || user.status}
                    color={statusConfig[user.status]?.color || 'default'}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  {user.last_login 
                    ? new Date(user.last_login).toLocaleDateString()
                    : 'Never'
                  }
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {user.project_count || 0} projects
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Tooltip title="Edit User">
                    <IconButton onClick={() => openEditDialog(user)}>
                      <EditIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Generate API Key">
                    <IconButton color="primary">
                      <VpnKeyIcon />
                    </IconButton>
                  </Tooltip>
                  {user.role !== 'super_admin' && (
                    <Tooltip title="Delete User">
                      <IconButton 
                        color="error" 
                        onClick={() => deleteUser(user.id)}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );

  const renderInvitationsTab = () => (
    <Box>
      <Typography variant="h6" mb={2}>
        Pending Invitations ({invitations.length})
      </Typography>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Email</TableCell>
              <TableCell>Role</TableCell>
              <TableCell>Invited By</TableCell>
              <TableCell>Sent Date</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {invitations.map((invitation) => (
              <TableRow key={invitation.id}>
                <TableCell>{invitation.email}</TableCell>
                <TableCell>
                  <Chip
                    icon={roles[invitation.role]?.icon}
                    label={roles[invitation.role]?.label || invitation.role}
                    color={roles[invitation.role]?.color || 'default'}
                    size="small"
                  />
                </TableCell>
                <TableCell>{invitation.invited_by_name}</TableCell>
                <TableCell>
                  {new Date(invitation.created_at).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <Chip
                    label={invitation.status}
                    color={invitation.status === 'pending' ? 'warning' : 'default'}
                    size="small"
                  />
                </TableCell>
                <TableCell align="right">
                  <Tooltip title="Resend Invitation">
                    <IconButton color="primary">
                      <SendIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Cancel Invitation">
                    <IconButton color="error">
                      <DeleteIcon />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );

  const renderAuditTab = () => (
    <Box>
      <Typography variant="h6" mb={2}>
        Recent Activity ({auditLogs.length})
      </Typography>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Timestamp</TableCell>
              <TableCell>User</TableCell>
              <TableCell>Action</TableCell>
              <TableCell>Resource</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>IP Address</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {auditLogs.map((log) => (
              <TableRow key={log.id}>
                <TableCell>
                  {new Date(log.timestamp).toLocaleString()}
                </TableCell>
                <TableCell>
                  {log.username || log.email || 'System'}
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {log.action.replace('_', ' ').toUpperCase()}
                  </Typography>
                </TableCell>
                <TableCell>
                  {log.resource_type && (
                    <Typography variant="caption">
                      {log.resource_type}: {log.resource_id}
                    </Typography>
                  )}
                </TableCell>
                <TableCell>
                  <Chip
                    label={log.success ? 'Success' : 'Failed'}
                    color={log.success ? 'success' : 'error'}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  <Typography variant="caption">
                    {log.ip_address || 'Unknown'}
                  </Typography>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Loading team data...</Typography>
      </Box>
    );
  }

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>
        <GroupIcon sx={{ mr: 2, verticalAlign: 'middle' }} />
        Team Management
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        Manage your team members, roles, and permissions. All actions are logged for security auditing.
      </Alert>

      <Paper sx={{ width: '100%' }}>
        <Tabs 
          value={activeTab} 
          onChange={(e, newValue) => setActiveTab(newValue)}
          indicatorColor="primary"
          textColor="primary"
        >
          <Tab label="Team Members" />
          <Tab label="Invitations" />
          <Tab label="Audit Log" />
        </Tabs>

        <Box p={3}>
          {activeTab === 0 && renderUsersTab()}
          {activeTab === 1 && renderInvitationsTab()}
          {activeTab === 2 && renderAuditTab()}
        </Box>
      </Paper>

      {/* Invite/Edit User Dialog */}
      <Dialog open={openDialog} onClose={handleDialogClose} maxWidth="sm" fullWidth>
        <DialogTitle>
          {dialogType === 'invite' ? 'Invite New User' : 'Edit User'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ pt: 1 }}>
            {dialogType === 'invite' ? (
              <>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Email Address"
                    type="email"
                    value={inviteForm.email}
                    onChange={(e) => setInviteForm({...inviteForm, email: e.target.value})}
                    required
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="First Name"
                    value={inviteForm.firstName}
                    onChange={(e) => setInviteForm({...inviteForm, firstName: e.target.value})}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="Last Name"
                    value={inviteForm.lastName}
                    onChange={(e) => setInviteForm({...inviteForm, lastName: e.target.value})}
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControl fullWidth>
                    <InputLabel>Role</InputLabel>
                    <Select
                      value={inviteForm.role}
                      onChange={(e) => setInviteForm({...inviteForm, role: e.target.value})}
                    >
                      {Object.entries(roles).map(([value, config]) => (
                        <MenuItem key={value} value={value}>
                          <Box display="flex" alignItems="center">
                            {config.icon}
                            <Box ml={1}>
                              <Typography variant="body2">{config.label}</Typography>
                              <Typography variant="caption" color="text.secondary">
                                {config.description}
                              </Typography>
                            </Box>
                          </Box>
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Personal Message (Optional)"
                    multiline
                    rows={3}
                    value={inviteForm.message}
                    onChange={(e) => setInviteForm({...inviteForm, message: e.target.value})}
                    placeholder="Add a personal message to the invitation email..."
                  />
                </Grid>
              </>
            ) : (
              <>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="First Name"
                    value={editForm.firstName}
                    onChange={(e) => setEditForm({...editForm, firstName: e.target.value})}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="Last Name"
                    value={editForm.lastName}
                    onChange={(e) => setEditForm({...editForm, lastName: e.target.value})}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Email"
                    type="email"
                    value={editForm.email}
                    onChange={(e) => setEditForm({...editForm, email: e.target.value})}
                  />
                </Grid>
                <Grid item xs={6}>
                  <FormControl fullWidth>
                    <InputLabel>Role</InputLabel>
                    <Select
                      value={editForm.role}
                      onChange={(e) => setEditForm({...editForm, role: e.target.value})}
                    >
                      {Object.entries(roles).map(([value, config]) => (
                        <MenuItem key={value} value={value}>
                          {config.icon} {config.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={6}>
                  <FormControl fullWidth>
                    <InputLabel>Status</InputLabel>
                    <Select
                      value={editForm.status}
                      onChange={(e) => setEditForm({...editForm, status: e.target.value})}
                    >
                      {Object.entries(statusConfig).map(([value, config]) => (
                        <MenuItem key={value} value={value}>
                          {config.icon} {config.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              </>
            )}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDialogClose}>Cancel</Button>
          <Button 
            onClick={handleSubmit} 
            variant="contained"
            disabled={dialogType === 'invite' && !inviteForm.email}
          >
            {dialogType === 'invite' ? 'Send Invitation' : 'Update User'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({...snackbar, open: false})}
      >
        <Alert 
          onClose={() => setSnackbar({...snackbar, open: false})} 
          severity={snackbar.severity}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default TeamManagement;

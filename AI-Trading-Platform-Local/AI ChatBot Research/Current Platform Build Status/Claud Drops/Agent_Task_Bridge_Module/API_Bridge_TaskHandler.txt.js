const express = require('express');
const router = express.Router();

const sharedContext = {
  taskQueue: {},
};

router.post('/bridge/agent-task', (req, res) => {
  const { agent, task, file, context, output_format } = req.body;

  if (!agent || !task) {
    return res.status(400).json({ error: 'Missing agent or task in request.' });
  }

  if (!sharedContext.taskQueue[agent]) {
    sharedContext.taskQueue[agent] = [];
  }

  const taskId = `task_${Date.now()}`;
  const taskDetails = {
    taskId,
    agent,
    task,
    file,
    context,
    output_format,
    status: 'queued',
    timestamp: new Date().toISOString()
  };

  sharedContext.taskQueue[agent].push(taskDetails);
  return res.json({ message: 'Task queued successfully.', task: taskDetails });
});

router.get('/bridge/task-queue', (req, res) => {
  const { agent } = req.query;

  if (!agent || !sharedContext.taskQueue[agent]) {
    return res.status(404).json({ error: 'No tasks found for this agent.' });
  }

  return res.json({ agent, tasks: sharedContext.taskQueue[agent] });
});

module.exports = router;

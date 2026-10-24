/**
 * Vercel Serverless Function Catch-All Entrypoint for /api/*
 */
const handleRequest = require('../server.js');

module.exports = (req, res) => {
  return handleRequest(req, res);
};

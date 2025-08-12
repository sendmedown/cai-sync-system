const { v4: uuidv4 } = require('uuid');

class PromptChainRouter {
  constructor(options = {}) {
    this.routes = options.routes || {};
    this.defaultRoute = options.defaultRoute || ((prompt) => ({ response: 'Default response', id: uuidv4() }));
    this.initialize();
  }

  initialize() {
    console.log('ðŸ”— PromptChainRouter initialized with routes:', Object.keys(this.routes));
  }

  addRoute(key, handler) {
    this.routes[key] = handler;
  }

  routePrompt(prompt) {
    const key = this.getRouteKey(prompt);
    const handler = this.routes[key] || this.defaultRoute;
    return handler(prompt);
  }

  getRouteKey(prompt) {
    if (prompt.includes('trading')) return 'trading';
    if (prompt.includes('deg')) return 'deg';
    return 'default';
  }

  integrateWithBridge(prompt, response) {
    if (global.wss) {
      global.wss.clients.forEach(client => {
        client.send(JSON.stringify({ type: 'prompt_response', prompt, response, id: uuidv4() }));
      });
    }
    return response;
  }

  integrateWithValidator(validator, response) {
    if (validator) {
      return validator.validate(response);
    }
    return response;
  }
}

module.exports = PromptChainRouter;

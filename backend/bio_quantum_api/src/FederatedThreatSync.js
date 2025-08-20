const EventEmitter = require("events");

class FederatedThreatSync {
  constructor(opts = {}) {
    this.opts = opts;
    this.bus = new EventEmitter();
    this.running = false;
  }
  start() {
    this.running = true;
    return { stop: () => { this.running = false; } };
  }
  publish(topic, payload) {
    try { this.bus.emit(topic, payload); } catch (_) {}
  }
  subscribe(topic, handler) {
    try { this.bus.on(topic, handler); } catch (_) {}
    return { unsubscribe: () => { try { this.bus.off(topic, handler); } catch (_) {} } };
  }
}

module.exports = FederatedThreatSync;

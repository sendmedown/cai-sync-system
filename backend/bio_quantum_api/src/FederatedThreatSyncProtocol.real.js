class FederatedThreatSyncProtocol {
  constructor(/* ... */) {}
  async initializeFederation(){ /* no-op */ }
  startThreatBroadcasting(){ /* no-op */ }
}
module.exports = FederatedThreatSyncProtocol;
// also support: const { FederatedThreatSyncProtocol } = require(...)
module.exports.FederatedThreatSyncProtocol = FederatedThreatSyncProtocol;

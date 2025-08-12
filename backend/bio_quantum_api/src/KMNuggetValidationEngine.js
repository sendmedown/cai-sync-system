const cosineSimilarity = require('compute-cosine-similarity');
const natural = require('natural');
const tokenizer = new natural.WordTokenizer();

class KMNuggetValidationEngine {
  constructor({ confidenceThreshold = 0.7, anomalyThreshold = 0.3 } = {}) {
    this.confidenceThreshold = confidenceThreshold;
    this.anomalyThreshold = anomalyThreshold;
  }

  computeConfidenceScore(nugget) {
    const sourceWeight = nugget.sourceCredibility || 0.3;
    const freshnessWeight = this._computeFreshnessWeight(nugget.timestamp);
    const historicalWeight = nugget.historicalAccuracy || 0.4;
    const volatilityWeight = nugget.volatilityCorrelation || 0.3;
    
    const weightedScore = (
      0.25 * sourceWeight +
      0.25 * freshnessWeight +
      0.25 * historicalWeight +
      0.25 * volatilityWeight
    );
    
    return Math.min(1.0, Math.max(0.0, weightedScore));
  }

  _computeFreshnessWeight(timestamp) {
    const hoursSince = (Date.now() - new Date(timestamp)) / 36e5;
    if (hoursSince < 1) return 1.0;
    if (hoursSince < 24) return 0.8;
    if (hoursSince < 168) return 0.6;
    return 0.3;
  }

  detectAnomaly(nugget, comparisonSet = []) {
    if (!comparisonSet.length) return false;
    
    const distances = comparisonSet.map(other => {
      const a = tokenizer.tokenize(nugget.text).map(t => t.toLowerCase());
      const b = tokenizer.tokenize(other.text).map(t => t.toLowerCase());
      return 1 - cosineSimilarity(a, b);
    });
    
    const avgDistance = distances.reduce((a, b) => a + b, 0) / distances.length;
    return avgDistance > this.anomalyThreshold;
  }

  validate(nugget, comparisonSet = []) {
    const confidence = this.computeConfidenceScore(nugget);
    const anomaly = this.detectAnomaly(nugget, comparisonSet);
    
    return {
      nuggetId: nugget.nuggetId,
      confidence,
      anomaly,
      valid: confidence >= this.confidenceThreshold && !anomaly
    };
  }
}

module.exports = KMNuggetValidationEngine;

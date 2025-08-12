const crypto = require('crypto');
const { v4: uuidv4 } = require('uuid');

class CodonGenerator {
  constructor(options = {}) {
    this.seed = options.seed || crypto.randomBytes(16).toString('hex');
    this.codonLength = options.codonLength || 4;
    this.alphabet = options.alphabet || ['A', 'C', 'G', 'T'];
    this.initialize();
  }

  initialize() {
    console.log('ðŸ§¬ CodonGenerator initialized with seed:', this.seed);
  }

  generateCodon() {
    let codon = '';
    for (let i = 0; i < this.codonLength; i++) {
      const randomIndex = crypto.createHash('sha256').update(this.seed + i).digest('hex') % this.alphabet.length;
      codon += this.alphabet[randomIndex];
    }
    return codon;
  }

  generateSequence(length = 10) {
    const sequence = [];
    for (let i = 0; i < length; i++) {
      sequence.push(this.generateCodon());
    }
    return sequence;
  }

  generateDegSequence(degData = {}, length = 10) {
    const seed = degData.seed || this.seed;
    const sequence = this.generateSequence(length);
    return {
      id: uuidv4(),
      sequence,
      degScore: degData.score || Math.random(),
      timestamp: new Date().toISOString()
    };
  }

  integrateWithValidator(validator, sequence) {
    if (validator) {
      return validator.validate(sequence);
    }
    return { valid: true, sequence };
  }
}

module.exports = CodonGenerator;

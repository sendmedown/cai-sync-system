(function() {
  // Install the Python to JavaScript compiler.
  const { execSync } = require('child_process');
  execSync('pip install py2js');

  // Compile the Python code to JavaScript.
  execSync('py2js bible_verse.py > bible_verse.js');

  // Open the HTML file in Chrome.
  execSync('start chrome bible_verse.html');
})();
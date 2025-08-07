const fs = require('fs');

function log(message) {
  fs.appendFileSync('C:/Users/richa/OneDrive/Documents/AI ChatBot Research/compile_and_open.log', message + '\n');
}

(function() {
  // Install the Python to JavaScript compiler.
  //const { execSync } = require('child_process');
  //log('Installing the Python to JavaScript compiler...');
  //execSync('pip install py2js');

  // Compile the Python code to JavaScript.
  log('Compiling the Python code to JavaScript...');
  execSync('py2js bible_verse.py > bible_verse.js');

  // Open the HTML file in Chrome OR brave.
  log('Opening the HTML file in brave...');
  execSync('start brave bible_verse.html');
})();


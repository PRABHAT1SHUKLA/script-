const fs = require('fs');
const path = require('path');
const css = require('css');

class CSSErrorFinder {
  constructor(options = {}) {
    this.rootDir = options.rootDir || process.cwd();
    this.extensions = options.extensions || ['.css', '.scss', '.sass', '.less'];
    this.errors = [];
    this.warnings = [];
  }

  // Find all CSS files recursively
  findCSSFiles(dir) {
    const files = [];
    
    const scan = (currentDir) => {
      const items = fs.readdirSync(currentDir);
      
      for (const item of items) {
        const fullPath = path.join(currentDir, item);
        const stat = fs.statSync(fullPath);
        
        if (stat.isDirectory() && !item.startsWith('.') && item !== 'node_modules') {
          scan(fullPath);
        } else if (stat.isFile() && this.extensions.some(ext => item.endsWith(ext))) {
          files.push(fullPath);
        }
      }
    };
    
    scan(dir);
    return files;
  }

  // Parse and validate CSS
  validateCSS(filePath, content) {
    const errors = [];
    
    try {
      // Try to parse CSS
      const parsed = css.parse(content, { silent: true });
      
      // Check for parsing errors
      if (parsed.stylesheet.parsingErrors && parsed.stylesheet.parsingErrors.length > 0) {
        parsed.stylesheet.parsingErrors.forEach(err => {
          errors.push({
            file: filePath,
            line: err.line,
            column: err.column,
            message: err.message,
            type: 'syntax-error'
          });
        });
      }
      
      // Additional checks
      this.checkRules(parsed.stylesheet.rules, filePath, errors);
      
    } catch (err) {
      errors.push({
        file: filePath,
        line: 1,
        column: 1,
        message: err.message,
        type: 'parse-error'
      });
    }
    
    return errors;
  }

  // Check CSS rules for common issues
  checkRules(rules, filePath, errors) {
    if (!rules) return;
    
    rules.forEach((rule, index) => {
      // Check for empty rulesets
      if (rule.type === 'rule' && (!rule.declarations || rule.declarations.length === 0)) {
        errors.push({
          file: filePath,
          line: rule.position?.start?.line || 0,
          column: rule.position?.start?.column || 0,
          message: `Empty ruleset: ${rule.selectors?.join(', ')}`,
          type: 'warning'
        });
      }
      
      // Check declarations
      if (rule.declarations) {
        rule.declarations.forEach(decl => {
          if (decl.type === 'declaration') {
            // Check for duplicate properties
            const duplicates = rule.declarations.filter(d => 
              d.type === 'declaration' && d.property === decl.property
            );
            
            if (duplicates.length > 1 && duplicates[0] === decl) {
              errors.push({
                file: filePath,
                line: decl.position?.start?.line || 0,
                column: decl.position?.start?.column || 0,
                message: `Duplicate property: ${decl.property}`,
                type: 'warning'
              });
            }
            
            // Check for invalid values
            if (!decl.value || decl.value.trim() === '') {
              errors.push({
                file: filePath,
                line: decl.position?.start?.line || 0,
                column: decl.position?.start?.column || 0,
                message: `Empty value for property: ${decl.property}`,
                type: 'error'
              });
            }
          }
        });
      }
      
      // Recursively check nested rules (media queries, etc.)
      if (rule.rules) {
        this.checkRules(rule.rules, filePath, errors);
      }
    });
  }

  // Generate report
  generateReport() {
    console.log('\n=== CSS Error Report ===\n');
    
    const errorCount = this.errors.filter(e => e.type !== 'warning').length;
    const warningCount = this.errors.filter(e => e.type === 'warning').length;
    
    console.log(`Total Errors: ${errorCount}`);
    console.log(`Total Warnings: ${warningCount}`);
    console.log(`Files Scanned: ${this.scannedFiles}\n`);
    
    if (this.errors.length === 0) {
      console.log('✓ No CSS errors found!\n');
      return;
    }
    
    // Group errors by file
    const errorsByFile = {};
    this.errors.forEach(err => {
      if (!errorsByFile[err.file]) {
        errorsByFile[err.file] = [];
      }
      errorsByFile[err.file].push(err);
    });
    
    // Print errors
    Object.keys(errorsByFile).forEach(file => {
      console.log(`\n${file}:`);
      errorsByFile[file].forEach(err => {
        const symbol = err.type === 'warning' ? '⚠' : '✗';
        console.log(`  ${symbol} Line ${err.line}:${err.column} - ${err.message}`);
      });
    });
    
    console.log('\n');
  }

  // Main scan function
  async scan() {
    console.log(`Scanning CSS files in: ${this.rootDir}\n`);
    
    const files = this.findCSSFiles(this.rootDir);
    this.scannedFiles = files.length;
    
    console.log(`Found ${files.length} CSS files\n`);
    
    for (const file of files) {
      try {
        const content = fs.readFileSync(file, 'utf8');
        const errors = this.validateCSS(file, content);
        this.errors.push(...errors);
      } catch (err) {
        console.error(`Error reading file ${file}:`, err.message);
      }
    }
    
    this.generateReport();
    
    return {
      totalErrors: this.errors.filter(e => e.type !== 'warning').length,
      totalWarnings: this.errors.filter(e => e.type === 'warning').length,
      errors: this.errors
    };
  }
}

// Usage
if (require.main === module) {
  const finder = new CSSErrorFinder({
    rootDir: process.argv[2] || process.cwd(),
    extensions: ['.css']
  });
  
  finder.scan().then(result => {
    process.exit(result.totalErrors > 0 ? 1 : 0);
  });
}

module.exports = CSSErrorFinder;

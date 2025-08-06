# Pre-Deployment Code Review Checklist

**Complete this review BEFORE deploying to AWS**

---

## SECURITY REVIEW ITEMS

### Secrets & API Keys
- [ ] **NO API keys in code files**
  - Search for: `sk-`, `api_key=`, `password=`, `secret=`
  - Check all .py, .js, .json, .yaml files
  
- [ ] **NO database passwords in code**
  - Search for: `DATABASE_URL=`, `DB_PASSWORD=`, connection strings
  
- [ ] **NO AWS credentials in code**
  - Search for: `AKIA`, `aws_access_key`, `aws_secret`
  
- [ ] **ALL secrets in .env file**
  - Verify .env is in .gitignore
  - Confirm .env.example exists with dummy values

### File Security
- [ ] **.gitignore properly configured**
  ```
  Must include:
  .env
  *.pem
  *.key
  /secrets/
  __pycache__/
  *.pyc
  .DS_Store
  ```

- [ ] **No sensitive data in logs**
  - Check all `print()` and `logger.info()` statements
  - Ensure no passwords/keys are logged

- [ ] **Input validation on all forms**
  - SQL injection protection
  - XSS prevention
  - File upload restrictions

### Authentication & Access
- [ ] **Strong password requirements enforced**
  - Minimum 12 characters
  - Mix of upper/lower/numbers/symbols
  
- [ ] **Session timeout configured**
  - Should be 30 minutes or less for legal data
  
- [ ] **Role-based access implemented**
  - Admin vs User permissions
  - Firm-level data isolation

---

## ENVIRONMENT VARIABLE CHECKS

### Required Variables Checklist
```env
# Database
- [ ] DATABASE_URL         # PostgreSQL connection
- [ ] REDIS_URL           # Redis connection

# API Keys
- [ ] OPENAI_API_KEY      # OpenAI API
- [ ] GROQ_API_KEY        # Groq API (if used)
- [ ] CLAUDE_API_KEY      # Claude API (if used)

# Security
- [ ] SECRET_KEY          # App secret (generate new!)
- [ ] ENCRYPTION_KEY      # For sensitive data

# AWS Configuration
- [ ] AWS_REGION          # Should be ap-southeast-2
- [ ] S3_BUCKET_NAME      # Document storage bucket

# Application
- [ ] APP_ENV             # production/staging/development
- [ ] LOG_LEVEL          # INFO for production
- [ ] ALLOWED_HOSTS      # Your domain names
```

### Environment File Template
- [ ] **Created .env.example with all variables**
- [ ] **NO real values in .env.example**
- [ ] **Instructions for each variable**

---

## DEPENDENCY AUDIT

### Python Dependencies
- [ ] **requirements.txt is up to date**
  ```bash
  pip freeze > requirements-check.txt
  # Compare with requirements.txt
  ```

- [ ] **No vulnerable packages**
  ```bash
  pip install safety
  safety check
  ```

- [ ] **Specific versions pinned**
  - Bad: `streamlit`
  - Good: `streamlit==1.31.0`

- [ ] **Remove unused packages**
  ```bash
  pip install pipreqs
  pipreqs . --force
  # Compare output with requirements.txt
  ```

### Security Vulnerabilities
- [ ] **Check for known vulnerabilities**
  ```bash
  # Install scanning tool
  pip install bandit
  
  # Scan code
  bandit -r . -f json -o bandit-report.json
  ```

- [ ] **Review high-severity issues**
  - Fix all HIGH severity issues
  - Document any FALSE positives

---

## PERFORMANCE OPTIMIZATION CHECKS

### Database Queries
- [ ] **Connection pooling enabled**
  ```python
  # Good - connection pooling
  engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=40)
  
  # Bad - no pooling
  engine = create_engine(DATABASE_URL)
  ```

- [ ] **Indexes on frequently queried fields**
  - user_id, firm_id, created_at
  - Check slow query log

- [ ] **N+1 queries eliminated**
  - Use eager loading for relationships
  - Batch queries where possible

### Caching Implementation
- [ ] **Redis caching configured**
  - Session storage
  - Frequently accessed data
  - AI response caching

- [ ] **Cache expiration set**
  ```python
  # Set appropriate TTL
  cache.set(key, value, timeout=3600)  # 1 hour
  ```

### Resource Limits
- [ ] **File upload limits set**
  ```python
  MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
  ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt'}
  ```

- [ ] **API rate limiting configured**
  - Per-user limits
  - Per-IP limits

- [ ] **Concurrent request limits**
  - Thread pool sizing
  - Connection limits

---

## BACKUP PLAN TEMPLATE

### Data Backup Strategy
- [ ] **Database backup schedule defined**
  ```
  Frequency: _________________ (recommend daily)
  Retention: _________________ (recommend 30 days)
  Type: [ ] Full [ ] Incremental
  ```

- [ ] **Document storage backup**
  ```
  S3 Versioning: [ ] Enabled
  Cross-region replication: [ ] Configured
  Lifecycle policies: [ ] Set
  ```

- [ ] **Backup testing procedure**
  ```
  Test frequency: _____________ (recommend monthly)
  Recovery time objective: _____ (recommend < 4 hours)
  Recovery point objective: ____ (recommend < 24 hours)
  ```

### Recovery Procedures
- [ ] **Database recovery documented**
  1. Identify backup to restore
  2. Create new RDS instance
  3. Restore from snapshot
  4. Update connection strings
  5. Test application

- [ ] **Application rollback plan**
  1. Keep previous Docker image
  2. Document rollback commands
  3. Test rollback procedure
  4. Communication plan

---

## CODE QUALITY CHECKS

### Python Code Standards
- [ ] **PEP 8 compliance**
  ```bash
  pip install flake8
  flake8 . --max-line-length=120
  ```

- [ ] **Type hints added**
  ```python
  # Good
  def process_document(file_path: str) -> dict:
  
  # Bad
  def process_document(file_path):
  ```

- [ ] **Docstrings for all functions**
  ```python
  def calculate_settlement(assets: list) -> dict:
      """
      Calculate property settlement distribution.
      
      Args:
          assets: List of asset dictionaries
          
      Returns:
          Dictionary with settlement calculations
      """
  ```

### Error Handling
- [ ] **All exceptions caught and logged**
  ```python
  try:
      result = risky_operation()
  except SpecificException as e:
      logger.error(f"Operation failed: {e}")
      # Handle gracefully
  ```

- [ ] **User-friendly error messages**
  - No stack traces shown to users
  - Clear instructions for resolution

- [ ] **Logging configured properly**
  ```python
  # Log to file, not console in production
  logging.basicConfig(
      filename='app.log',
      level=logging.INFO,
      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  )
  ```

---

## LEGAL COMPLIANCE CHECKS

### Data Privacy
- [ ] **Privacy policy updated**
  - Data collection disclosed
  - Third-party services listed
  - Retention periods specified

- [ ] **Data encryption implemented**
  - At rest (database, S3)
  - In transit (HTTPS)
  - Sensitive fields encrypted

- [ ] **Audit logging enabled**
  ```python
  # Log all data access
  logger.info(f"User {user_id} accessed case {case_id}")
  ```

### Australian Legal Requirements
- [ ] **Data residency confirmed**
  - All services in ap-southeast-2
  - No data leaves Australia

- [ ] **Professional disclaimers added**
  - "Not legal advice" warnings
  - Jurisdiction limitations
  - Terms of service

- [ ] **User consent mechanisms**
  - Terms acceptance required
  - Cookie consent (if applicable)
  - Data processing agreement

---

## FINAL REVIEW CHECKLIST

### Documentation
- [ ] **README.md updated**
  - Installation instructions
  - Configuration guide
  - Troubleshooting section

- [ ] **API documentation current**
  - All endpoints documented
  - Example requests/responses
  - Error codes explained

- [ ] **User guide created**
  - Screenshots included
  - Common tasks explained
  - FAQ section

### Testing
- [ ] **All tests passing**
  ```bash
  python -m pytest
  ```

- [ ] **Test coverage > 80%**
  ```bash
  pytest --cov=app --cov-report=html
  ```

- [ ] **Load testing completed**
  - Can handle expected users
  - Performance acceptable
  - No memory leaks

### Sign-offs
- [ ] **Security review completed**
  - Reviewed by: _______________ Date: ___/___/___
  
- [ ] **Code review completed**
  - Reviewed by: _______________ Date: ___/___/___
  
- [ ] **Legal review completed**
  - Reviewed by: _______________ Date: ___/___/___
  
- [ ] **Final approval to deploy**
  - Approved by: _______________ Date: ___/___/___

---

## DEPLOYMENT READINESS SCORE

Rate each area (1-5, where 5 is excellent):

- [ ] Security: ___/5
- [ ] Performance: ___/5
- [ ] Code Quality: ___/5
- [ ] Documentation: ___/5
- [ ] Testing: ___/5
- [ ] Compliance: ___/5

**Total Score: ___/30**

**Minimum score to deploy: 24/30**

---

## ISSUES TO RESOLVE

List any issues found during review:

1. _________________________________________________
2. _________________________________________________
3. _________________________________________________
4. _________________________________________________
5. _________________________________________________

**All issues must be resolved before deployment!**

---

*This checklist ensures your code is secure, performant, and compliant before going live on AWS.*
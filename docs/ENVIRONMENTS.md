# Environment Configuration Guide

## Overview
This document describes the environment setup and deployment process for the Ollama Hub infrastructure.

## Environment Structure
We maintain three distinct environments:

### Development (dev)
- **Purpose**: Development and testing
- **Domain**: dev.example.com
- **Features**:
  - Debug mode enabled
  - Extended logging
  - Increased resource limits
  - Frequent health checks
  - Debug endpoints enabled

### Staging (staging)
- **Purpose**: Pre-production testing and validation
- **Domain**: staging.example.com
- **Features**:
  - Production-like configuration
  - Performance monitoring
  - Daily backups
  - Moderate resource constraints
  - Alert thresholds for monitoring

### Production (prod)
- **Purpose**: Live production environment
- **Domain**: example.com
- **Features**:
  - High availability enabled
  - Strict security policies
  - Hourly backups with encryption
  - Rate limiting
  - PagerDuty integration
  - Optimized resource allocation

## Deployment Infrastructure

### Base Components
- Traefik for routing and load balancing
- Docker and Docker Compose for containerization
- NVIDIA Container Runtime for GPU support
- Prometheus and Grafana for monitoring

### Service Stack
1. **Ollama Service**
   - Memory: 14GB
   - GPU access enabled
   - Health monitoring

2. **Open WebUI**
   - Memory: 500MB (prod/staging) to 1GB (dev)
   - Replicated in production

3. **Qdrant**
   - Memory: 2GB to 3GB
   - Persistent storage
   - Regular backups

4. **RAG API**
   - Memory: 500MB to 1GB
   - Replicated in production
   - Auto-scaling enabled

5. **Grafana**
   - Memory: 500MB
   - Custom dashboards
   - Environment-specific credentials

## Deployment Process

### Prerequisites
1. Install Ansible
2. Configure SSH access to target servers
3. Set up environment-specific variables
4. Encrypt sensitive data with ansible-vault

### Deployment Commands
```bash
# Deploy to Development
ansible-playbook -i inventory/dev site.yml -e "target_env=dev"

# Deploy to Staging
ansible-playbook -i inventory/staging site.yml -e "target_env=staging"

# Deploy to Production
ansible-playbook -i inventory/prod site.yml -e "target_env=prod"
```

### Environment Variables
Environment-specific configurations are managed through:
- group_vars/all/main.yml: Common variables
- group_vars/dev/vars.yml: Development settings
- group_vars/staging/vars.yml: Staging settings
- group_vars/prod/vars.yml: Production settings
- group_vars/all/vault.yml: Encrypted sensitive data

## Monitoring and Alerts

### Health Checks
- Development: 15s interval, 5 retries
- Staging: 20s interval, 3 retries
- Production: 30s interval, 3 retries

### Alert Thresholds
Production:
- Memory: 80%
- CPU: 75%
- Error Rate: 1%

Staging:
- Memory: 85%
- CPU: 80%
- Error Rate: 5%

### Monitoring Tools
- Grafana dashboards
- Prometheus metrics
- Alert Manager
- PagerDuty (Production only)
- Slack notifications

## Backup Strategy

### Development
- Type: Basic
- Frequency: On-demand
- Retention: None

### Staging
- Type: Full
- Frequency: Daily
- Retention: 7 days

### Production
- Type: Full with encryption
- Frequency: Hourly
- Retention: 30 days
- Encryption: Enabled

## Security Considerations

### Production Security Measures
- SSL/TLS enabled
- Strict CORS policy
- Rate limiting enabled
- Audit logging
- Regular security updates
- Access control via SSH keys
- Encrypted sensitive data

### Access Control
- Development: Team access
- Staging: Limited team access
- Production: Admin-only access

## Troubleshooting

### Common Issues
1. Service Health Checks
   - Check logs: `docker-compose logs [service]`
   - Verify resource limits
   - Check network connectivity

2. Deployment Failures
   - Verify ansible-vault secrets
   - Check SSH access
   - Validate environment variables

3. Performance Issues
   - Monitor resource usage
   - Check Grafana dashboards
   - Verify service configurations

### Support Contacts
- Development: dev-team@example.com
- Staging: ops-team@example.com
- Production: on-call@example.com

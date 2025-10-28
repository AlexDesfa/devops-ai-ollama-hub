# Infrastructure Provisioning and Management

## Table of Contents
1. [Development Environment Provisioning](#development-environment-provisioning)
2. [Staging and Production Management](#staging-and-production-management)
3. [CI/CD Integration](#cicd-integration)
4. [Security Measures](#security-measures)

## Development Environment Provisioning

### Ansible Infrastructure

Our development environment is provisioned using Ansible with the following structure:

```
ansible/
├── inventory/
│   └── dev                    # Development inventory
├── group_vars/
│   ├── all/
│   │   ├── main.yml          # Common variables
│   │   └── vault.yml         # Encrypted secrets
│   └── dev/
│       └── vars.yml          # Dev-specific variables
└── roles/
    ├── common/               # Base system setup
    ├── docker/               # Docker installation
    └── app/                  # Application deployment
```

### Provisioning Process

1. **Base System Setup** (common role)
   ```yaml
   # System updates and basic packages
   - name: Update system
     apt:
       update_cache: yes
       upgrade: yes

   # System configurations
   - name: Configure system settings
     sysctl:
       name: vm.max_map_count
       value: '262144'
       state: present

   # Monitoring setup
   - name: Install monitoring agents
     apt:
       name: node-exporter
       state: present
   ```

2. **Docker Environment** (docker role)
   ```yaml
   # Docker installation and configuration
   - name: Install Docker
     apt:
       name:
         - docker-ce
         - docker-ce-cli
         - containerd.io
       state: present

   # NVIDIA Container Runtime
   - name: Install NVIDIA Docker
     apt:
       name: nvidia-docker2
       state: present

   # Network setup
   - name: Create Docker networks
     docker_network:
       name: "{{ item }}"
       state: present
     loop:
       - internal
       - monitoring
   ```

3. **Application Deployment** (app role)
   - Service deployment using docker-compose
   - Health check configuration
   - Log management setup

## Staging and Production Management

### Environment Separation

1. **Inventory Structure**
   ```ini
   # inventory/staging
   [staging]
   staging-1 ansible_host=10.0.1.1
   staging-2 ansible_host=10.0.1.2

   [staging:vars]
   env=staging
   monitoring_level=detailed

   # inventory/prod
   [prod]
   prod-1 ansible_host=10.0.2.1
   prod-2 ansible_host=10.0.2.2

   [prod:vars]
   env=production
   monitoring_level=critical
   ```

2. **Environment-Specific Variables**
   ```yaml
   # group_vars/staging/vars.yml
   domain_suffix: staging.example.com
   debug_mode: false
   memory_limits:
     ollama: "14g"
     qdrant: "2g"
     rag_api: "750m"

   # group_vars/prod/vars.yml
   domain_suffix: example.com
   debug_mode: false
   ha_enabled: true
   memory_limits:
     ollama: "28g"
     qdrant: "4g"
     rag_api: "1g"
   ```

### Resource Management

1. **Scaling Configuration**
   ```yaml
   # Production scaling
   replicas:
     rag_api: 3
     openwebui: 2

   # Resource limits
   resource_limits:
     cpu:
       dev: "0.5"
       staging: "1.0"
       prod: "2.0"
     memory:
       dev: "1G"
       staging: "2G"
       prod: "4G"
   ```

2. **Storage Configuration**
   ```yaml
   storage_config:
     dev:
       type: local
       backup: false
     staging:
       type: persistent
       backup: daily
     prod:
       type: persistent
       backup: hourly
       replication: true
   ```

## CI/CD Integration

### GitHub Actions Integration

1. **Infrastructure Provisioning**
   ```yaml
   jobs:
     provision:
       steps:
         - name: Install Ansible
           run: pip install ansible

         - name: Load environment config
           run: |
             echo "${{ secrets.ANSIBLE_VAULT_PASSWORD }}" > vault.key
             ansible-vault decrypt group_vars/all/vault.yml --vault-password-file vault.key

         - name: Run Ansible playbook
           run: |
             ansible-playbook site.yml -i inventory/$ENV \
               --vault-password-file vault.key
   ```

2. **Deployment Process**
   - Environment validation
   - Infrastructure updates
   - Application deployment
   - Health checks

### Deployment Workflow

1. **Pre-deployment Checks**
   ```bash
   # Verify environment readiness
   ansible-playbook verify.yml -i inventory/$ENV

   # Check infrastructure state
   ansible-playbook check.yml -i inventory/$ENV
   ```

2. **Deployment Execution**
   ```bash
   # Infrastructure updates
   ansible-playbook site.yml -i inventory/$ENV --tags infrastructure

   # Application deployment
   ansible-playbook site.yml -i inventory/$ENV --tags application
   ```

## Security Measures

### Network Security

1. **Firewall Configuration**
   ```yaml
   firewall_rules:
     # Load Balancer access
     - port: 80
       source: load_balancer_subnet
       protocol: tcp
     - port: 443
       source: load_balancer_subnet
       protocol: tcp

     # Monitoring access
     - port: 9100
       source: monitoring_subnet
       protocol: tcp

     # SSH access
     - port: 22
       source: vpn_subnet
       protocol: tcp
   ```

2. **Network Segmentation**
   ```yaml
   network_zones:
     public:
       - load_balancers
     private:
       - application_servers
       - database_servers
     management:
       - monitoring_servers
       - bastion_hosts
   ```

### Access Management

1. **User Access**
   ```yaml
   user_policies:
     dev:
       - group: developers
         permissions: [deploy, restart]
     staging:
       - group: senior_developers
         permissions: [deploy, restart, logs]
     prod:
       - group: operators
         permissions: [deploy, restart, logs]
       - group: admins
         permissions: [all]
   ```

2. **Secret Management**
   ```yaml
   secret_rotation:
     ssh_keys: 30  # days
     api_tokens: 90  # days
     certificates: 365  # days

   vault_configuration:
     encryption: aes-256-cbc
     key_shares: 5
     key_threshold: 3
   ```

### Monitoring and Compliance

1. **Security Monitoring**
   ```yaml
   security_monitoring:
     log_retention: 90  # days
     alerts:
       - failed_login_attempts
       - sudo_usage
       - file_integrity
       - network_anomalies
   ```

2. **Compliance Checks**
   ```yaml
   compliance_policies:
     - security_updates: automatic
     - password_policy: strong
     - disk_encryption: required
     - audit_logging: enabled
   ```

### Disaster Recovery

1. **Backup Strategy**
   ```yaml
   backup_policy:
     dev:
       frequency: weekly
       retention: 1  # month
     staging:
       frequency: daily
       retention: 1  # month
     prod:
       frequency: hourly
       retention: 3  # months
       encryption: true
   ```

2. **Recovery Procedures**
   ```yaml
   recovery_procedures:
     - verify_backup_integrity
     - restore_infrastructure
     - validate_data
     - verify_application
   ```

## Usage Instructions

1. **Development Environment**
   ```bash
   # Provision development environment
   ansible-playbook site.yml -i inventory/dev -e "target_env=dev"
   ```

2. **Staging Environment**
   ```bash
   # Provision staging environment
   ansible-playbook site.yml -i inventory/staging -e "target_env=staging"
   ```

3. **Production Environment**
   ```bash
   # Provision production environment
   ansible-playbook site.yml -i inventory/prod -e "target_env=prod"

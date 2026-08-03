# netris-test-infra

OSAC test infrastructure that deploys and tests OpenShift Assisted Cluster on a simulated Netris Spectrum-X GPU cluster. Tests three service models: VMaaS, BMaaS (planned), and CaaS.

Uses [netris-lab](netris-lab/) as a git submodule for the underlying network infrastructure.

## Project Structure

```
roles/                          # Ansible roles (each has tasks/main.yml)
  setup-infra/                  # Prerequisites, cache, OCP/OSAC tool installs
  deploy-infra/                 # Orchestrates netris-lab submodule roles
  configure-netris/             # Create VPC/VNet/Subnet/NAT via Netris API
  configure-dns/                # Route 53 + dnsmasq DNS for OCP
  restore-ocp/                  # Deploy OCP from snapshot: CoW disks, recert, boot, health check
  cache-snapshot/               # Pull + cache flavor OCI image (skopeo)
  prep-osac/                    # Clone mono-repo, patch Helm values (fresh install)
  prep-refresh-osac/            # Clone mono-repo, patch values, rebuild CLI (snapshot refresh)
  patch-osac-refresh/           # Post-refresh: patch Netris config + SSH keys into running cluster
  discover-caas/                # Boot discovery VMs with InfraEnv ISO
  setup-caas/                   # Label agents, register host type
  create-caas/                  # Create CaaS cluster via fulfillment API
  destroy-infra/                # Teardown netris-lab
  destroy-caas/                 # Teardown CaaS resources
playbooks/                      # Ansible playbooks (one per workflow phase)
inventory/
  local.yml                     # Inventory (localhost, local connection)
  group_vars/all.yml            # All configuration variables
netris-lab/                     # Git submodule — see its own CLAUDE.md
vendor/                         # Vendored Ansible collections
```

## Commands

```
make deploy                 # Full pipeline: deploy-infra + deploy-ocp + deploy-osac (fresh Helm install)
make deploy-fast            # Snapshot pipeline: deploy-infra + deploy-ocp + deploy-osac (snapshot refresh)
make setup-infra            # Install prerequisites, cache images + snapshot flavor
make deploy-infra           # Deploy netris-lab
make deploy-ocp             # Configure Netris networking + restore OCP SNO from snapshot
make deploy-osac            # Deploy OSAC (fresh Helm install or snapshot refresh based on OSAC_DEPLOY_MODE)
make connectivity           # Re-run lab connectivity (VPN, BGP, softgate agents)
make setup-caas             # CaaS setup: discover hosts, label agents, register host type
make deploy-caas            # CaaS: create cluster
make destroy-full           # Teardown all infrastructure
make destroy-osac           # Teardown OSAC only
make destroy-ocp            # Reset OCP for reinstall
make destroy-infra          # Teardown netris-lab
make destroy-caas           # Teardown CaaS resources
make vendor-update          # Refresh vendored Ansible collections
make gather-infra           # Gather diagnostic info from the cluster
# Override variables: make <target> EXTRA_VARS="key=value"
# Image overrides: make deploy-osac EXTRA_VARS="fulfillment_service_image=quay.io/..."
```

## Workflow Order

**Full deploy (fresh):** deploy (deploy-infra → deploy-ocp → deploy-osac)

**Snapshot deploy (fast):** deploy-fast (deploy-infra → deploy-ocp → deploy-osac with OSAC_DEPLOY_MODE=snapshot)

**CaaS:** deploy or deploy-fast → setup-caas → deploy-caas

## Ansible Configuration

- Inventory: `inventory/local.yml`
- Roles path: `roles:netris-lab/roles` (both local and submodule roles)
- Collections: `vendor:netris-lab/collections`
- Netris API calls use `netris.controller.*` collection modules

## Configuration

All variables in `inventory/group_vars/all.yml`. Key sections:

- **Lab**: `netris_lab_dir`, `ew_fabric_enable`
- **OCP VM sizing**: `ocp_server_vcpu`, `ocp_server_memory_gb`, disk sizes
- **Netris networking**: `ocp_vpc_name`, `ocp_subnet_cidr`, SNAT/DNAT IPs
- **OCP install**: `ocp_version`, `ocp_cluster_name`, `ocp_base_domain`
- **OSAC**: `osac_repo/branch`, `osac_namespace`, `osac_values_file`
- **Component images**: `osac_operator_image`, `fulfillment_service_image` (empty = defaults)
- **Snapshot**: `snapshot_flavor_image`, `snapshot_flavor_dir`, `snapshot_recert_image`, `snapshot_osac_namespace`, `snapshot_osac_values_file`
- **CaaS**: `caas_discovery_vm_patterns`, `caas_host_type_id`, `caas_cluster_name`, `caas_agents`

## External Dependencies

- **osac** — mono-repo cloned to `/opt/osac` during `prep-osac` (installer at `/opt/osac/osac-installer`)
- **fulfillment-service** — cloned to `$HOME/.local/src/fulfillment-service` (job-scoped, non-root); `osac` CLI built from its Go code to `$HOME/.local/bin/osac`
- **aicli** — CLI for Red Hat Assisted Installer (pip install)
- **Credentials**: pull secret at `/root/pull-secret`, SSH key at `/root/.ssh/id_rsa.pub`

## Conventions

- Ansible roles follow standard structure: `tasks/main.yml`, `templates/`, `defaults/`
- Templates use Jinja2 (`.j2` extension)
- VM operations use `virsh`, `virt-xml`, `qemu-img` via shell/command modules
- Kubernetes resources applied via `kubernetes.core.k8s` or `oc`/`kubectl` CLI
- Waits/retries use `until` loops with `retries` and `delay`

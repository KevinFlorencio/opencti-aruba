# Backup and restore

Two layers, because they fail differently: the OpenCTI graph (Elasticsearch) and
the VM disk (Proxmox).

## Elasticsearch snapshots

The stack mounts `backups/es` into the Elasticsearch container at
`/usr/share/elasticsearch/backups` and starts ES with
`-Epath.repo=/usr/share/elasticsearch/backups`.

Register the repository once (the name is referenced by the policy):

```bash
curl -s -X PUT "http://127.0.0.1:9200/_snapshot/aruba-nvme" \
  -H 'Content-Type: application/json' \
  -d '{"type":"fs","settings":{"location":"/usr/share/elasticsearch/backups","compress":true}}'
```

Create a daily snapshot policy at 02:30, keeping 14 days:

```bash
curl -s -X PUT "http://127.0.0.1:9200/_slm/policy/aruba-daily" \
  -H 'Content-Type: application/json' \
  -d '{
    "schedule": "0 30 2 * * ?",
    "name": "<aruba-{now/d}>",
    "repository": "aruba-nvme",
    "config": {"indices": "*", "include_global_state": true},
    "retention": {"expire_after": "14d", "min_count": 3, "max_count": 14}
  }'
```

Run one immediately and inspect:

```bash
curl -s -X POST "http://127.0.0.1:9200/_slm/policy/aruba-daily/_execute"
curl -s "http://127.0.0.1:9200/_snapshot/aruba-nvme/_all?pretty"
```

A snapshot on the same physical disk is not disaster recovery. After the VM is
on NVMe, keep a second copy off the host (Proxmox `vzdump` to the USB disk, or
restic to object storage). The snapshot is for "I broke the graph, restore it",
not "the house burned down".

### Restore a snapshot

`opencti` and `worker` must be stopped first. Restoring closes the indices; do
not do this while a connector is writing.

```bash
cd ~/aruba-ti
docker compose stop opencti worker
curl -s -X POST "http://127.0.0.1:9200/_snapshot/aruba-nvme/<snapshot>/_restore?wait_for_completion=true" \
  -H 'Content-Type: application/json' \
  -d '{"indices":"*","include_global_state":true}'
docker compose start opencti worker
```

Then check `GET _cluster/health` and the OpenCTI home page. If the restore
reports conflicting open indices, close them first with
`POST /<index>/_close` and retry.

## Proxmox VM backup

From the Proxmox host:

```bash
vzdump 124 --storage hdd --mode snapshot --compress zstd --notes-template 'opencti-aruba pre-change'
```

`--mode snapshot` keeps the VM running. The archive lands in
`/mnt/hdd/dump/`. Verify it with `vzdump --verify` if the storage supports it.

## Restore the VM

```bash
qmrestore /mnt/hdd/dump/vzdump-qemu-124-<timestamp>.vma.zst 124 --storage local-lvm
```

Do not restore over a running VM. Detach or rename the existing disk first, or
restore under a new VM ID and switch the IP after verification.

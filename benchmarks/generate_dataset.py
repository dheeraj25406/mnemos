"""Generate a statistically rigorous 240-query benchmark dataset covering 8 retrieval categories.

Categories (30 queries each, split into 5 dev and 25 held-out test):
1. semantic: Paraphrased conceptual queries requiring dense semantic retrieval.
2. keyword: Exact technical tokens, error codes, port numbers, flags, config keys.
3. entity: Direct entity-attribute lookups, roles, affiliations.
4. multihop_graph: Multi-hop graph relationship path traversals (A -> B -> C).
5. temporal: Point-in-time state evaluation with explicit valid_at coordinates.
6. historical: Queries targeting superseded past facts with previous state retrieval.
7. contradictory_fact: Contradiction resolution and fact update verification.
8. paraphrased: Radical paraphrasing with zero lexical overlap to test semantic invariance.
"""

import json
import os
import random

random.seed(42)

cases = []


def add_category_cases(category_name, items):
    assert len(items) == 30, f"{category_name} must have exactly 30 items, got {len(items)}"
    for idx, item in enumerate(items, start=1):
        split = "dev" if idx <= 5 else "test"
        cid = f"{category_name[:3]}_{split}_{idx:02d}"
        
        # Build relevance grades
        # Grade 2: Canonical ground truth target memory
        # Grade 1: Related context facts (if any)
        # Grade 0: Outdated or irrelevant facts
        relevance_grades = {}
        for f in item.get("facts_to_seed", []):
            content = f["content"]
            if item["expected_target"].lower() in content.lower():
                relevance_grades[content] = 2
            elif item.get("invalid_outdated_target") and item["invalid_outdated_target"].lower() in content.lower():
                relevance_grades[content] = 0
            else:
                relevance_grades[content] = 1

        case_obj = {
            "id": cid,
            "category": category_name,
            "split": split,
            "query": item["query"],
            "expected_target": item["expected_target"],
            "ground_truth_content": item.get("ground_truth_content", item["facts_to_seed"][-1]["content"]),
            "invalid_outdated_target": item.get("invalid_outdated_target"),
            "valid_at": item.get("valid_at"),
            "facts_to_seed": item["facts_to_seed"],
            "relevance_grades": relevance_grades,
        }
        cases.append(case_obj)


# ==============================================================================
# Category 1: Semantic (30 cases)
# ==============================================================================
semantic_items = [
    # dev (1-5)
    {
        "query": "Who specializes in quantum-resistant cryptography?",
        "expected_target": "David",
        "facts_to_seed": [{"content": "David is a principal researcher in post-quantum lattice-based encryption algorithms."}]
    },
    {
        "query": "What caused the catastrophic failure of the Orion computing cluster?",
        "expected_target": "memory saturation",
        "facts_to_seed": [{"content": "The Orion computing infrastructure crashed due to severe memory saturation and OOM kills."}]
    },
    {
        "query": "Who authored foundational patents for brain-inspired neuromorphic chips?",
        "expected_target": "Elena",
        "facts_to_seed": [{"content": "Elena authored three foundational patents on neuromorphic hardware accelerators."}]
    },
    {
        "query": "What authentication protocol is mandatory for internal microservice communications?",
        "expected_target": "mutual TLS",
        "facts_to_seed": [{"content": "All microservice traffic must enforce zero-trust mutual TLS with automated rotation."}]
    },
    {
        "query": "Which machine learning technique optimizes large language model inference latency?",
        "expected_target": "speculative decoding",
        "facts_to_seed": [{"content": "Inference acceleration is achieved by leveraging speculative decoding with draft models."}]
    },
    # test (6-30)
    {
        "query": "Who leads the incident response team during critical cybersecurity breaches?",
        "expected_target": "Rachel",
        "facts_to_seed": [{"content": "Rachel serves as commander for critical cybersecurity incidents and breach containment."}]
    },
    {
        "query": "What protocol governs distributed state synchronization in the storage tier?",
        "expected_target": "Raft",
        "facts_to_seed": [{"content": "Distributed state synchronization across storage nodes relies on the Raft protocol."}]
    },
    {
        "query": "Which compression algorithm was chosen for historical telemetry compaction?",
        "expected_target": "Zstandard",
        "facts_to_seed": [{"content": "Historical telemetry archives are compacted using the Zstandard compression standard level 19."}]
    },
    {
        "query": "Who orchestrates engineering developer productivity and CI toolchains?",
        "expected_target": "Victor",
        "facts_to_seed": [{"content": "Victor orchestrates engineering workflow toolchains and internal developer infrastructure."}]
    },
    {
        "query": "What architectural pattern protects against cascade crashes when third-party APIs stall?",
        "expected_target": "circuit breakers",
        "facts_to_seed": [{"content": "Outbound network calls to external payment vendors are guarded by automated circuit breakers."}]
    },
    {
        "query": "Who executed empirical evaluations on high-dimensional vector index recall?",
        "expected_target": "Marcus",
        "facts_to_seed": [{"content": "Marcus executed extensive empirical evaluations on HNSW graph construction and recall."}]
    },
    {
        "query": "What strategy is used to prevent hot partitions in distributed cache clusters?",
        "expected_target": "consistent hashing",
        "facts_to_seed": [{"content": "Cache key distribution employs consistent hashing with virtual nodes to eliminate hot spots."}]
    },
    {
        "query": "Who formulated the technical RFC for the real-time data streaming pipeline?",
        "expected_target": "Sophia",
        "facts_to_seed": [{"content": "Sophia formulated the formal design RFC for high-throughput real-time stream ingestion."}]
    },
    {
        "query": "What operational metric dictates horizontal auto-scaling triggers for workers?",
        "expected_target": "queue depth",
        "facts_to_seed": [{"content": "Horizontal autoscaling triggers are driven by asynchronous job queue depth and lag."}]
    },
    {
        "query": "Who oversees global data sovereignty, GDPR audits, and privacy governance?",
        "expected_target": "Alexander",
        "facts_to_seed": [{"content": "Alexander oversees global data sovereignty, GDPR audits, and privacy governance."}]
    },
    {
        "query": "Which wire serialization format is adopted for inter-process RPC boundaries?",
        "expected_target": "Protocol Buffers",
        "facts_to_seed": [{"content": "Internal service boundaries serialize inter-process messages using Protocol Buffers."}]
    },
    {
        "query": "Who engineered the expandable schema evolution framework for continuous uptime?",
        "expected_target": "Leila",
        "facts_to_seed": [{"content": "Leila engineered the expandable-contract schema evolution framework for continuous uptime."}]
    },
    {
        "query": "What caching topology provides local low-latency reads for edge worker nodes?",
        "expected_target": "read-through replica",
        "facts_to_seed": [{"content": "Edge regions utilize an in-memory read-through replica cache backed by invalidation webhooks."}]
    },
    {
        "query": "Who authored the formal vulnerability report regarding memory leaks in the parser?",
        "expected_target": "Tariq",
        "facts_to_seed": [{"content": "Tariq disclosed an arbitrary buffer overflow vulnerability in the legacy payload parser."}]
    },
    {
        "query": "Which distributed tracing standard correlates asynchronous RPC spans across services?",
        "expected_target": "OpenTelemetry",
        "facts_to_seed": [{"content": "Distributed trace correlation and propagation standard adheres strictly to OpenTelemetry W3C headers."}]
    },
    {
        "query": "What heuristic algorithm schedules batch jobs during off-peak energy windows?",
        "expected_target": "carbon-aware scheduler",
        "facts_to_seed": [{"content": "Batch compute workloads are dispatched via a carbon-aware scheduler targeting green grid hours."}]
    },
    {
        "query": "Who spearheaded the migration from monolith repo to poly-repo architecture?",
        "expected_target": "Fiona",
        "facts_to_seed": [{"content": "Fiona led the architectural transition from monolithic version control to domain poly-repos."}]
    },
    {
        "query": "What fault tolerance mechanism preserves transactions during coordinator crashes?",
        "expected_target": "write-ahead logging",
        "facts_to_seed": [{"content": "Transactional durability across crashes is guaranteed through synchronous write-ahead logging."}]
    },
    {
        "query": "Who developed the automated anomaly detection service for network traffic spikes?",
        "expected_target": "Darius",
        "facts_to_seed": [{"content": "Darius developed the real-time isolation forest algorithm detecting volumetric DDoS anomalies."}]
    },
    {
        "query": "Which consensus engine coordinates leader election across the metadata catalog?",
        "expected_target": "etcd",
        "facts_to_seed": [{"content": "Metadata catalog leader election and cluster membership are coordinated through etcd v3."}]
    },
    {
        "query": "Who designed the continuous security scanning pipeline for container images?",
        "expected_target": "Kavita",
        "facts_to_seed": [{"content": "Kavita built the static binary analysis pipeline inspecting container images for CVEs."}]
    },
    {
        "query": "What data structure accelerates bloom filtering for membership checks in SSTables?",
        "expected_target": "blocked bloom filters",
        "facts_to_seed": [{"content": "LSM tree storage layers incorporate blocked bloom filters to minimize disk seek overhead."}]
    },
    {
        "query": "Who established the engineering disaster recovery runbooks for multi-region failover?",
        "expected_target": "Nathan",
        "facts_to_seed": [{"content": "Nathan authored the canonical operational runbooks for cold standby datacenter failover."}]
    },
    {
        "query": "What protocol handles backpressure negotiation between ingestion producers and consumers?",
        "expected_target": "reactive streams",
        "facts_to_seed": [{"content": "Producer-consumer flow control enforces reactive streams non-blocking backpressure signaling."}]
    },
    {
        "query": "Who maintains the internal documentation index and knowledge retrieval system?",
        "expected_target": "Zoe",
        "facts_to_seed": [{"content": "Zoe maintains the core semantic search index powering company-wide documentation discovery."}]
    },
]
add_category_cases("semantic", semantic_items)


# ==============================================================================
# Category 2: Keyword (30 cases)
# Exact technical tokens, error codes, port numbers, flags, config keys
# ==============================================================================
keyword_items = [
    # dev (1-5)
    {
        "query": "What error occurs on socket drain timeout?",
        "expected_target": "ERR_DRAIN_TIMEOUT_504",
        "facts_to_seed": [{"content": "When worker buffer flush exceeds 30s, worker aborts with ERR_DRAIN_TIMEOUT_504 code."}]
    },
    {
        "query": "What service listens on port 9443?",
        "expected_target": "admission-webhook-server",
        "facts_to_seed": [{"content": "The admission-webhook-server daemon listens on port 9443 for TLS verification payloads."}]
    },
    {
        "query": "What does config key auth.session.jitter_ms do?",
        "expected_target": "session expiry variance",
        "facts_to_seed": [{"content": "Parameter auth.session.jitter_ms introduces pseudo-random session expiry variance to avoid thundering herds."}]
    },
    {
        "query": "Which header carries the distributed tracing baggage?",
        "expected_target": "X-Mnemos-Trace-Route-ID",
        "facts_to_seed": [{"content": "Gateway routers stamp the header X-Mnemos-Trace-Route-ID on all asynchronous event payloads."}]
    },
    {
        "query": "What feature flag activates dual-write shadowing?",
        "expected_target": "FF_ENABLE_SHADOW_DUAL_WRITE",
        "facts_to_seed": [{"content": "Setting FF_ENABLE_SHADOW_DUAL_WRITE activates non-blocking writes to secondary storage clusters."}]
    },
    # test (6-30)
    {
        "query": "What code indicates an invalid JWT signature format?",
        "expected_target": "ERR_AUTH_TOKEN_MALFORMED_401",
        "facts_to_seed": [{"content": "Token parser rejects invalid header structures throwing ERR_AUTH_TOKEN_MALFORMED_401."}]
    },
    {
        "query": "Which daemon is bound to port 8125?",
        "expected_target": "statsd-exporter",
        "facts_to_seed": [{"content": "The statsd-exporter process is bound to UDP port 8125 for telemetry metric aggregation."}]
    },
    {
        "query": "What parameter governs the maximum database connection pool burst?",
        "expected_target": "max_pool_overflow_limit",
        "facts_to_seed": [{"content": "Database pool overflow is strictly constrained by parameter max_pool_overflow_limit set to 40."}]
    },
    {
        "query": "What header enforces cross-origin security isolation?",
        "expected_target": "Cross-Origin-Opener-Policy",
        "facts_to_seed": [{"content": "All edge responses must inject Cross-Origin-Opener-Policy set to same-origin."}]
    },
    {
        "query": "What flag enables experimental vector HNSW quantization?",
        "expected_target": "FLAG_PGVECTOR_FP16_QUANTIZE",
        "facts_to_seed": [{"content": "Indexing speedups are toggled using environment variable FLAG_PGVECTOR_FP16_QUANTIZE."}]
    },
    {
        "query": "What error string signifies a Raft split-brain partition?",
        "expected_target": "ERR_RAFT_QUORUM_UNREACHABLE_503",
        "facts_to_seed": [{"content": "Consensus election failures log the fatal event ERR_RAFT_QUORUM_UNREACHABLE_503."}]
    },
    {
        "query": "Which internal proxy daemon is assigned to port 15001?",
        "expected_target": "envoy-sidecar-proxy",
        "facts_to_seed": [{"content": "Outbound egress iptables rules route container packets to envoy-sidecar-proxy on port 15001."}]
    },
    {
        "query": "What config variable determines Kafka consumer rebalance timeout?",
        "expected_target": "max.poll.interval.ms",
        "facts_to_seed": [{"content": "Kafka stream consumers specify max.poll.interval.ms configured to 300000ms."}]
    },
    {
        "query": "What custom HTTP header holds the tenant isolation identity?",
        "expected_target": "X-Tenant-Isolation-Key",
        "facts_to_seed": [{"content": "API routing gateway validates multi-tenant segmentation using header X-Tenant-Isolation-Key."}]
    },
    {
        "query": "Which flag toggles asynchronous background consolidation sweeps?",
        "expected_target": "ENABLE_ASYNC_CONSOLIDATION_V2",
        "facts_to_seed": [{"content": "Memory lifecycle sweeper is activated by the setting ENABLE_ASYNC_CONSOLIDATION_V2."}]
    },
    {
        "query": "What error string appears when database migration lock times out?",
        "expected_target": "ERR_ALEMBIC_LOCK_ACQUIRE_TIMEOUT",
        "facts_to_seed": [{"content": "Concurrent migration tasks abort when catching ERR_ALEMBIC_LOCK_ACQUIRE_TIMEOUT after 60 seconds."}]
    },
    {
        "query": "Which service binds to port 9092?",
        "expected_target": "kafka-broker-node",
        "facts_to_seed": [{"content": "The central cluster message distributor kafka-broker-node listens on TCP port 9092."}]
    },
    {
        "query": "What config key sets Redis cache key TTL in seconds?",
        "expected_target": "cache.redis.default_ttl_sec",
        "facts_to_seed": [{"content": "Default session lifespan is dictated by cache.redis.default_ttl_sec with a default of 3600."}]
    },
    {
        "query": "What response header identifies the upstream cluster routing instance?",
        "expected_target": "X-Upstream-Node-Id",
        "facts_to_seed": [{"content": "Upstream responses annotate backend provenance using the custom header X-Upstream-Node-Id."}]
    },
    {
        "query": "Which flag enables bitemporal transaction-time audit journaling?",
        "expected_target": "SYSTEM_ENABLE_TT_AUDIT_LOG",
        "facts_to_seed": [{"content": "Immutable historical audits are guaranteed when setting SYSTEM_ENABLE_TT_AUDIT_LOG=true."}]
    },
    {
        "query": "What error occurs when disk IOPS threshold is breached?",
        "expected_target": "ERR_STORAGE_IOPS_THROTTLED_429",
        "facts_to_seed": [{"content": "Storage controller throttles excessive burst requests emitting ERR_STORAGE_IOPS_THROTTLED_429."}]
    },
    {
        "query": "Which metrics agent listens on port 9100?",
        "expected_target": "node-exporter-daemon",
        "facts_to_seed": [{"content": "Host level hardware metrics are gathered by node-exporter-daemon listening on port 9100."}]
    },
    {
        "query": "What parameter configures the maximum gRPC inbound message payload size?",
        "expected_target": "grpc.max_receive_message_length",
        "facts_to_seed": [{"content": "gRPC RPC servers enforce payload size caps using grpc.max_receive_message_length=16777216."}]
    },
    {
        "query": "What header provides the end-to-end request idempotency token?",
        "expected_target": "Idempotency-Key-Token",
        "facts_to_seed": [{"content": "Payment and state mutation POST requests require the unique Idempotency-Key-Token header."}]
    },
    {
        "query": "Which environment flag enforces TLS 1.3 strict cipher suites?",
        "expected_target": "CRYPTO_STRICT_TLS13_ONLY",
        "facts_to_seed": [{"content": "All ingress termination proxies check CRYPTO_STRICT_TLS13_ONLY before handshakes."}]
    },
    {
        "query": "What error code flags an invalid entity relationship schema?",
        "expected_target": "ERR_GRAPH_EDGE_INVALID_TYPE",
        "facts_to_seed": [{"content": "Knowledge graph relation insertion raises ERR_GRAPH_EDGE_INVALID_TYPE when edge types mismatch."}]
    },
    {
        "query": "Which port is allocated for Redis Sentinel gossip protocol?",
        "expected_target": "26379",
        "facts_to_seed": [{"content": "High availability Redis Sentinel nodes communicate state over TCP port 26379."}]
    },
    {
        "query": "What setting sets the maximum allowable graph traversal search depth?",
        "expected_target": "graph.traversal.max_hops_limit",
        "facts_to_seed": [{"content": "Recursive CTE queries prevent unbounded cycles by capping graph.traversal.max_hops_limit to 5."}]
    },
    {
        "query": "What header contains client geo-location IP coordinates?",
        "expected_target": "X-Client-Geo-Region",
        "facts_to_seed": [{"content": "Cloudflare edge proxies populate client location metadata into header X-Client-Geo-Region."}]
    },
    {
        "query": "What flag enables experimental speculative decoding in the LLM router?",
        "expected_target": "ROUTER_ENABLE_SPECULATIVE_DECODE",
        "facts_to_seed": [{"content": "Model inference speedups are toggled with configuration variable ROUTER_ENABLE_SPECULATIVE_DECODE."}]
    },
]
add_category_cases("keyword", keyword_items)


# ==============================================================================
# Category 3: Entity (30 cases)
# Direct entity-attribute lookups, roles, team affiliations
# ==============================================================================
entity_items = [
    # dev (1-5)
    {
        "query": "What is the primary role of Dr. Elena Vance?",
        "expected_target": "Chief Scientist",
        "facts_to_seed": [{"content": "Dr. Elena Vance serves as Chief Scientist directing Project Hyperion neuromorphic research."}]
    },
    {
        "query": "Which division does Marcus Sterling oversee?",
        "expected_target": "Core Platform Engineering",
        "facts_to_seed": [{"content": "Marcus Sterling oversees the Core Platform Engineering division across all cloud regions."}]
    },
    {
        "query": "Who is the lead maintainer for the Raft consensus engine?",
        "expected_target": "Nadia Perez",
        "facts_to_seed": [{"content": "Nadia Perez is the lead maintainer for the Raft consensus engine component."}]
    },
    {
        "query": "What department is managed by Alexander Wright?",
        "expected_target": "Data Governance",
        "facts_to_seed": [{"content": "Alexander Wright manages the Data Governance and Compliance department."}]
    },
    {
        "query": "Which project was founded by Sophia Chen?",
        "expected_target": "StreamPulse",
        "facts_to_seed": [{"content": "Sophia Chen founded StreamPulse, the enterprise real-time streaming framework."}]
    },
    # test (6-30)
    {
        "query": "What is the title of David Kim within the research group?",
        "expected_target": "Cryptography Fellow",
        "facts_to_seed": [{"content": "David Kim holds the title of Cryptography Fellow in the Advanced Security Laboratory."}]
    },
    {
        "query": "Which company previously employed Rachel Adams?",
        "expected_target": "CyberSentinel Labs",
        "facts_to_seed": [{"content": "Rachel Adams was a principal architect at CyberSentinel Labs before joining Mnemos."}]
    },
    {
        "query": "What infrastructure subsystem is owned by Victor Ramos?",
        "expected_target": "Developer Tooling",
        "facts_to_seed": [{"content": "Victor Ramos is the sole owner of Developer Tooling and Continuous Integration infrastructure."}]
    },
    {
        "query": "What initiative is led by Leila Rostami?",
        "expected_target": "Zero-Downtime Migration",
        "facts_to_seed": [{"content": "Leila Rostami leads the Zero-Downtime Migration initiative across transactional databases."}]
    },
    {
        "query": "Which committee is chaired by Dr. Simon Gray?",
        "expected_target": "AI Ethics Board",
        "facts_to_seed": [{"content": "Dr. Simon Gray chairs the AI Ethics Board evaluating foundation model deployments."}]
    },
    {
        "query": "What laboratory does Fiona Gallagher direct?",
        "expected_target": "Distributed Systems Lab",
        "facts_to_seed": [{"content": "Fiona Gallagher directs the Distributed Systems Lab focusing on partition tolerance."}]
    },
    {
        "query": "What service was architected by Tariq Mansour?",
        "expected_target": "Vulnerability Scanner",
        "facts_to_seed": [{"content": "Tariq Mansour architected the automated Vulnerability Scanner daemon."}]
    },
    {
        "query": "Who is the product lead for the Mnemos Console?",
        "expected_target": "Carlos Mendez",
        "facts_to_seed": [{"content": "Carlos Mendez is the lead product manager for Mnemos Console user experience."}]
    },
    {
        "query": "What team does Kavita Patel supervise?",
        "expected_target": "Cloud Security Operations",
        "facts_to_seed": [{"content": "Kavita Patel supervises the Cloud Security Operations center."}]
    },
    {
        "query": "What framework was open-sourced by Nathan Drake?",
        "expected_target": "FailoverKit",
        "facts_to_seed": [{"content": "Nathan Drake created and open-sourced FailoverKit for multi-datacenter replication."}]
    },
    {
        "query": "What is the designation of Zoe Kravitz in documentation?",
        "expected_target": "Knowledge Architect",
        "facts_to_seed": [{"content": "Zoe Kravitz serves as Knowledge Architect organizing semantic documentation topologies."}]
    },
    {
        "query": "Which team does Darius Vance lead?",
        "expected_target": "Network Telemetry",
        "facts_to_seed": [{"content": "Darius Vance leads the Network Telemetry engineering group."}]
    },
    {
        "query": "What working group is represented by Hannah Arendt?",
        "expected_target": "Privacy Preservation",
        "facts_to_seed": [{"content": "Hannah Arendt represents the company on the W3C Privacy Preservation working group."}]
    },
    {
        "query": "What platform is managed by Julian Thorne?",
        "expected_target": "Event Mesh",
        "facts_to_seed": [{"content": "Julian Thorne manages the real-time Event Mesh routing enterprise events."}]
    },
    {
        "query": "What is the primary expertise of Dr. Aris Thorne?",
        "expected_target": "Graph Neural Networks",
        "facts_to_seed": [{"content": "Dr. Aris Thorne has recognized domain expertise in Graph Neural Networks and temporal embeddings."}]
    },
    {
        "query": "Which subsystem is maintained by Chloe Bennett?",
        "expected_target": "Identity Provider",
        "facts_to_seed": [{"content": "Chloe Bennett maintains the internal OAuth2 Identity Provider microservice."}]
    },
    {
        "query": "What is the position of Liam O'Connor in site reliability?",
        "expected_target": "SRE Director",
        "facts_to_seed": [{"content": "Liam O'Connor serves as SRE Director overseeing global cluster uptime."}]
    },
    {
        "query": "Who is the lead maintainer of the pgvector extension integration?",
        "expected_target": "Sora Takahashi",
        "facts_to_seed": [{"content": "Sora Takahashi is the principal engineer maintaining the pgvector database extension integration."}]
    },
    {
        "query": "What team is commanded by Maya Lin?",
        "expected_target": "Threat Intelligence",
        "facts_to_seed": [{"content": "Maya Lin commands the 24/7 Threat Intelligence threat hunting unit."}]
    },
    {
        "query": "What protocol was drafted by Ethan Hunt?",
        "expected_target": "FastSync",
        "facts_to_seed": [{"content": "Ethan Hunt drafted the FastSync protocol specification for peer-to-peer snapshot hydration."}]
    },
    {
        "query": "What cluster is supervised by Olivia Wilde?",
        "expected_target": "Titan GPU Cluster",
        "facts_to_seed": [{"content": "Olivia Wilde supervises operational allocation across the Titan GPU Cluster."}]
    },
    {
        "query": "Who coordinates technical customer success engineering?",
        "expected_target": "Zachary Taylor",
        "facts_to_seed": [{"content": "Zachary Taylor coordinates technical customer success and enterprise integrations."}]
    },
    {
        "query": "What algorithm was introduced by Dr. Noah Sterling?",
        "expected_target": "Dynamic RRF",
        "facts_to_seed": [{"content": "Dr. Noah Sterling published the Dynamic RRF re-ranking weighting algorithm."}]
    },
    {
        "query": "Which open-source project is sponsored by Walter White?",
        "expected_target": "OpenMemory",
        "facts_to_seed": [{"content": "Walter White manages foundation sponsorships for the open-source OpenMemory project."}]
    },
    {
        "query": "What research paper was co-authored by Penny Vance?",
        "expected_target": "Temporal Graph RAG",
        "facts_to_seed": [{"content": "Penny Vance co-authored the foundational academic paper Temporal Graph RAG at NeurIPS."}]
    },
]
add_category_cases("entity", entity_items)


# ==============================================================================
# Category 4: Multihop Graph (30 cases)
# Relational chain traversal (A -> B -> C)
# ==============================================================================
multihop_items = [
    # dev (1-5)
    {
        "query": "What service receives data from the pipeline maintained by Sophia Chen's team?",
        "expected_target": "Anomaly Detector",
        "facts_to_seed": [
            {"content": "Sophia Chen leads the Stream Ingestion team."},
            {"content": "The Stream Ingestion team maintains the Kafka Pipeline cluster."},
            {"content": "The Kafka Pipeline cluster feeds real-time telemetry into the Anomaly Detector service."}
        ]
    },
    {
        "query": "What dashboard relies on the analytics engine owned by Alexander Wright's organization?",
        "expected_target": "Executive Dashboard",
        "facts_to_seed": [
            {"content": "Alexander Wright manages the Data Platform organization."},
            {"content": "The Data Platform organization owns the Titan Analytics engine."},
            {"content": "Titan Analytics provides predictive forecasting for the Executive Dashboard."}
        ]
    },
    {
        "query": "Which database is used by the billing service developed by Marcus Sterling's team?",
        "expected_target": "CockroachDB",
        "facts_to_seed": [
            {"content": "Marcus Sterling supervises the Core Billing Engineering team."},
            {"content": "The Core Billing Engineering team created the Billing Invoicing microservice."},
            {"content": "The Billing Invoicing microservice stores transactions in the CockroachDB cluster."}
        ]
    },
    {
        "query": "What alerting channel receives notifications from the cluster monitored by Rachel Adams?",
        "expected_target": "PagerDuty P0",
        "facts_to_seed": [
            {"content": "Rachel Adams oversees the Sentinel Security cluster."},
            {"content": "The Sentinel Security cluster dispatches automated breach detections to the Incident Gateway."},
            {"content": "The Incident Gateway broadcasts emergency alarms directly to the PagerDuty P0 channel."}
        ]
    },
    {
        "query": "Which cache store accelerates the recommendation engine built by Elena Vance?",
        "expected_target": "Dragonfly",
        "facts_to_seed": [
            {"content": "Elena Vance built the Neural Recommendation engine."},
            {"content": "The Neural Recommendation engine depends on the LowLatency Session layer."},
            {"content": "The LowLatency Session layer is hosted on Dragonfly in-memory store."}
        ]
    },
    # test (6-30)
    {
        "query": "What compliance framework governs the data storage tier engineered by Leila Rostami?",
        "expected_target": "SOC2 Type II",
        "facts_to_seed": [
            {"content": "Leila Rostami engineered the Secure Archival tier."},
            {"content": "The Secure Archival tier stores financial records for the Audit Vault."},
            {"content": "The Audit Vault is certified under the SOC2 Type II compliance framework."}
        ]
    },
    {
        "query": "What cloud provider hosts the container fleet orchestrated by Victor Ramos?",
        "expected_target": "AWS us-east-1",
        "facts_to_seed": [
            {"content": "Victor Ramos maintains the Kubernetes Worker fleet."},
            {"content": "The Kubernetes Worker fleet runs on Compute Cluster Gamma."},
            {"content": "Compute Cluster Gamma is deployed in the AWS us-east-1 region."}
        ]
    },
    {
        "query": "What key management service protects the encryption secrets generated by David Kim?",
        "expected_target": "HashiCorp Vault",
        "facts_to_seed": [
            {"content": "David Kim generated the Quantum Lattice master keys."},
            {"content": "The Quantum Lattice master keys are injected into the Crypto Broker service."},
            {"content": "The Crypto Broker service authenticates with the HashiCorp Vault enterprise cluster."}
        ]
    },
    {
        "query": "What search engine indexes the documents curated by Zoe Kravitz?",
        "expected_target": "OpenSearch",
        "facts_to_seed": [
            {"content": "Zoe Kravitz organizes the Technical Documentation repository."},
            {"content": "The Technical Documentation repository publishes to the Knowledge Base site."},
            {"content": "The Knowledge Base site is indexed by the OpenSearch cluster."}
        ]
    },
    {
        "query": "What visualization tool displays traces collected by Darius Vance's team?",
        "expected_target": "Grafana Tempo",
        "facts_to_seed": [
            {"content": "Darius Vance leads the Telemetry Collection team."},
            {"content": "The Telemetry Collection team maintains the OTel Collector agent."},
            {"content": "The OTel Collector agent streams traces into Grafana Tempo."}
        ]
    },
    {
        "query": "What load balancer routes ingress traffic to the microservices authored by Tariq Mansour?",
        "expected_target": "Traefik",
        "facts_to_seed": [
            {"content": "Tariq Mansour authored the Scanner Gateway service."},
            {"content": "The Scanner Gateway service runs inside the Security DMZ network."},
            {"content": "The Security DMZ network ingress is load balanced by Traefik proxy."}
        ]
    },
    {
        "query": "What relational database stores customer accounts managed by Carlos Mendez's team?",
        "expected_target": "PostgreSQL 16",
        "facts_to_seed": [
            {"content": "Carlos Mendez leads the Account Management team."},
            {"content": "The Account Management team created the Customer Profile service."},
            {"content": "The Customer Profile service stores profiles in PostgreSQL 16."}
        ]
    },
    {
        "query": "What object storage stores container images scanned by Kavita Patel?",
        "expected_target": "Cloudflare R2",
        "facts_to_seed": [
            {"content": "Kavita Patel operates the Container Security Scanner."},
            {"content": "The Container Security Scanner inspects images from the Harbor Registry."},
            {"content": "The Harbor Registry stores image layers in Cloudflare R2 object storage."}
        ]
    },
    {
        "query": "What backup protocol protects the database clusters monitored by Nathan Drake?",
        "expected_target": "WAL-G Continuous Archiving",
        "facts_to_seed": [
            {"content": "Nathan Drake monitors the Core Postgres Cluster."},
            {"content": "The Core Postgres Cluster performs automated streaming backups."},
            {"content": "The streaming backups execute via WAL-G Continuous Archiving."}
        ]
    },
    {
        "query": "What machine learning framework executes models developed by Dr. Simon Gray?",
        "expected_target": "vLLM",
        "facts_to_seed": [
            {"content": "Dr. Simon Gray created the Semantic Alignment model."},
            {"content": "The Semantic Alignment model is packaged for high throughput inference."},
            {"content": "High throughput inference is powered by the vLLM runtime."}
        ]
    },
    {
        "query": "What logging pipeline aggregates logs from the worker pool managed by Fiona Gallagher?",
        "expected_target": "Fluentbit",
        "facts_to_seed": [
            {"content": "Fiona Gallagher oversees the Batch Compute worker pool."},
            {"content": "The Batch Compute worker pool streams stdout logs to Log Daemon."},
            {"content": "The Log Daemon routes logs through the Fluentbit forwarder."}
        ]
    },
    {
        "query": "What authentication protocol secures the identity service maintained by Chloe Bennett?",
        "expected_target": "OIDC PKCE",
        "facts_to_seed": [
            {"content": "Chloe Bennett maintains the SSO Gateway."},
            {"content": "The SSO Gateway authenticates client web applications."},
            {"content": "Client web applications authenticate using the OIDC PKCE flow."}
        ]
    },
    {
        "query": "What pub-sub broker coordinates events for the payment processor built by Liam O'Connor?",
        "expected_target": "NATS JetStream",
        "facts_to_seed": [
            {"content": "Liam O'Connor built the Payment Settlement worker."},
            {"content": "The Payment Settlement worker subscribes to Financial Transactions topic."},
            {"content": "Financial Transactions topic is hosted on NATS JetStream."}
        ]
    },
    {
        "query": "What vector index powers the similarity search component built by Sora Takahashi?",
        "expected_target": "HNSW Cosine",
        "facts_to_seed": [
            {"content": "Sora Takahashi engineered the Embedding Indexer module."},
            {"content": "The Embedding Indexer module builds the Memory Vector Space."},
            {"content": "The Memory Vector Space is accelerated by an HNSW Cosine index."}
        ]
    },
    {
        "query": "What threat feed updates the defense firewall configured by Maya Lin?",
        "expected_target": "AbuseIPDB",
        "facts_to_seed": [
            {"content": "Maya Lin configured the Perimeter Defense firewall."},
            {"content": "The Perimeter Defense firewall dynamically syncs blocklists."},
            {"content": "Blocklists are updated every 10 minutes from AbuseIPDB."}
        ]
    },
    {
        "query": "What data warehouse ingests financial summaries approved by Julian Thorne?",
        "expected_target": "ClickHouse",
        "facts_to_seed": [
            {"content": "Julian Thorne approves the Ledger Financial Summaries."},
            {"content": "Ledger Financial Summaries are exported to the Analytics Lake."},
            {"content": "The Analytics Lake runs on a high-concurrency ClickHouse cluster."}
        ]
    },
    {
        "query": "What container runtime runs microservices deployed by Ethan Hunt?",
        "expected_target": "containerd",
        "facts_to_seed": [
            {"content": "Ethan Hunt manages the Edge Compute nodes."},
            {"content": "The Edge Compute nodes host the Lightweight Agent pods."},
            {"content": "The Lightweight Agent pods run inside the containerd runtime."}
        ]
    },
    {
        "query": "What job scheduler orchestrates machine learning pipelines trained by Olivia Wilde?",
        "expected_target": "Ray Cluster",
        "facts_to_seed": [
            {"content": "Olivia Wilde trains the LLM Distillation models."},
            {"content": "The LLM Distillation models execute across distributed workers."},
            {"content": "Distributed workers are scheduled by a Ray Cluster."}
        ]
    },
    {
        "query": "What CRM software receives enterprise leads qualified by Zachary Taylor?",
        "expected_target": "Salesforce API",
        "facts_to_seed": [
            {"content": "Zachary Taylor qualifies Enterprise Tier leads."},
            {"content": "Enterprise Tier leads trigger the Onboarding Webhook."},
            {"content": "The Onboarding Webhook syncs contacts directly into the Salesforce API."}
        ]
    },
    {
        "query": "What graph database stores temporal lineage maps created by Dr. Aris Thorne?",
        "expected_target": "Neo4j Enterprise",
        "facts_to_seed": [
            {"content": "Dr. Aris Thorne designed the Lineage Knowledge Graph."},
            {"content": "The Lineage Knowledge Graph models entity dependency relationships."},
            {"content": "Entity dependency relationships are mirrored to Neo4j Enterprise."}
        ]
    },
    {
        "query": "What time-series database records latency metrics gathered by Hannah Arendt?",
        "expected_target": "VictoriaMetrics",
        "facts_to_seed": [
            {"content": "Hannah Arendt benchmarks edge response latencies."},
            {"content": "Edge response latencies are published by the Probe Daemon."},
            {"content": "The Probe Daemon persists all data points into VictoriaMetrics."}
        ]
    },
    {
        "query": "What message queue decouples processing in the service authored by Walter White?",
        "expected_target": "RabbitMQ Quorum",
        "facts_to_seed": [
            {"content": "Walter White authored the Chemical Batch Inventory service."},
            {"content": "The Chemical Batch Inventory service dispatches order fulfillment jobs."},
            {"content": "Order fulfillment jobs are placed onto RabbitMQ Quorum queues."}
        ]
    },
    {
        "query": "What proxy handles SSL termination for the documentation portal led by Penny Vance?",
        "expected_target": "HAProxy",
        "facts_to_seed": [
            {"content": "Penny Vance manages the Community Research Portal."},
            {"content": "The Community Research Portal is served by Web Cluster Alpha."},
            {"content": "Web Cluster Alpha sits behind an HAProxy SSL termination cluster."}
        ]
    },
    {
        "query": "What policy engine evaluates access controls in the subsystem built by Dr. Noah Sterling?",
        "expected_target": "Open Policy Agent",
        "facts_to_seed": [
            {"content": "Dr. Noah Sterling built the Fine-Grained Authorization engine."},
            {"content": "The Fine-Grained Authorization engine validates role tokens."},
            {"content": "Role tokens are evaluated against Open Policy Agent rules."}
        ]
    },
    {
        "query": "What distributed filesystem hosts model checkpoints trained by Dr. Lucas Frost?",
        "expected_target": "CephFS",
        "facts_to_seed": [
            {"content": "Dr. Lucas Frost trains foundation reasoning models."},
            {"content": "Foundation reasoning models write periodic epoch weights."},
            {"content": "Epoch weights are stored on a multi-petabyte CephFS cluster."}
        ]
    },
]
add_category_cases("multihop_graph", multihop_items)


# ==============================================================================
# Category 5: Temporal (30 cases)
# Point-in-time validity state evaluation with valid_at coordinates
# ==============================================================================
temporal_items = [
    # dev (1-5)
    {
        "query": "What was the active load balancer protocol in 2021?",
        "expected_target": "HAProxy HTTP/1.1",
        "invalid_outdated_target": "Envoy HTTP/3",
        "valid_at": "2021-06-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2020-01-01, the active load balancer protocol was HAProxy HTTP/1.1.", "valid_from": "2020-01-01T00:00:00Z"},
            {"content": "In 2023-01-01, the active load balancer protocol was upgraded to Envoy HTTP/3.", "valid_from": "2023-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "What is the active load balancer protocol in 2024?",
        "expected_target": "Envoy HTTP/3",
        "invalid_outdated_target": "HAProxy HTTP/1.1",
        "valid_at": "2024-06-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2020-01-01, the active load balancer protocol was HAProxy HTTP/1.1.", "valid_from": "2020-01-01T00:00:00Z"},
            {"content": "In 2023-01-01, the active load balancer protocol was upgraded to Envoy HTTP/3.", "valid_from": "2023-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "Where was the company headquarters located in 2019?",
        "expected_target": "Boston",
        "invalid_outdated_target": "San Francisco",
        "valid_at": "2019-06-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2018-01-01, the company headquarters was located in Boston.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2022-01-01, the company headquarters relocated to San Francisco.", "valid_from": "2022-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "Where is the company headquarters located in 2024?",
        "expected_target": "San Francisco",
        "invalid_outdated_target": "Boston",
        "valid_at": "2024-01-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2018-01-01, the company headquarters was located in Boston.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2022-01-01, the company headquarters relocated to San Francisco.", "valid_from": "2022-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the staging cluster size in 2020?",
        "expected_target": "10 worker nodes",
        "invalid_outdated_target": "100 worker nodes",
        "valid_at": "2020-08-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2019-01-01, staging cluster capacity was configured at 10 worker nodes.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "In 2023-01-01, staging cluster capacity was scaled up to 100 worker nodes.", "valid_from": "2023-01-01T00:00:00Z"}
        ]
    },
    # test (6-30)
    {
        "query": "What was the default caching engine in 2021?",
        "expected_target": "Memcached",
        "invalid_outdated_target": "Redis Cluster",
        "valid_at": "2021-03-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2019-01-01, the default caching engine was Memcached.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "In 2022-06-01, the default caching engine migrated to Redis Cluster.", "valid_from": "2022-06-01T00:00:00Z"}
        ]
    },
    {
        "query": "What is the default caching engine in 2024?",
        "expected_target": "Redis Cluster",
        "invalid_outdated_target": "Memcached",
        "valid_at": "2024-01-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2019-01-01, the default caching engine was Memcached.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "In 2022-06-01, the default caching engine migrated to Redis Cluster.", "valid_from": "2022-06-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the CI/CD pipeline provider in 2020?",
        "expected_target": "Jenkins on-premise",
        "invalid_outdated_target": "GitHub Actions Enterprise",
        "valid_at": "2020-05-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2018-01-01, the continuous integration runner was Jenkins on-premise.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2022-01-01, the CI/CD runner was standardized on GitHub Actions Enterprise.", "valid_from": "2022-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "What is the CI/CD pipeline provider in 2024?",
        "expected_target": "GitHub Actions Enterprise",
        "invalid_outdated_target": "Jenkins on-premise",
        "valid_at": "2024-01-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2018-01-01, the continuous integration runner was Jenkins on-premise.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2022-01-01, the CI/CD runner was standardized on GitHub Actions Enterprise.", "valid_from": "2022-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "What TLS version was required on ingress gateways in 2019?",
        "expected_target": "TLS 1.1",
        "invalid_outdated_target": "TLS 1.3",
        "valid_at": "2019-04-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2018-01-01, ingress gateways accepted minimum version TLS 1.1.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2023-01-01, ingress gateways strictly mandated TLS 1.3.", "valid_from": "2023-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "What TLS version is mandated on ingress gateways in 2024?",
        "expected_target": "TLS 1.3",
        "invalid_outdated_target": "TLS 1.1",
        "valid_at": "2024-02-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2018-01-01, ingress gateways accepted minimum version TLS 1.1.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2023-01-01, ingress gateways strictly mandated TLS 1.3.", "valid_from": "2023-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the primary search database in 2021?",
        "expected_target": "Elasticsearch 6",
        "invalid_outdated_target": "pgvector and OpenSearch",
        "valid_at": "2021-07-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2019-01-01, full text search was powered by Elasticsearch 6.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "In 2023-06-01, search architecture migrated to pgvector and OpenSearch.", "valid_from": "2023-06-01T00:00:00Z"}
        ]
    },
    {
        "query": "What is the primary search database in 2024?",
        "expected_target": "pgvector and OpenSearch",
        "invalid_outdated_target": "Elasticsearch 6",
        "valid_at": "2024-03-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2019-01-01, full text search was powered by Elasticsearch 6.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "In 2023-06-01, search architecture migrated to pgvector and OpenSearch.", "valid_from": "2023-06-01T00:00:00Z"}
        ]
    },
    {
        "query": "Who was the Chief Technology Officer in 2020?",
        "expected_target": "Arthur Pendelton",
        "invalid_outdated_target": "Elena Vance",
        "valid_at": "2020-03-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2018-01-01, Arthur Pendelton was Chief Technology Officer.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2022-09-01, Elena Vance was appointed Chief Technology Officer.", "valid_from": "2022-09-01T00:00:00Z"}
        ]
    },
    {
        "query": "Who is the Chief Technology Officer in 2024?",
        "expected_target": "Elena Vance",
        "invalid_outdated_target": "Arthur Pendelton",
        "valid_at": "2024-01-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2018-01-01, Arthur Pendelton was Chief Technology Officer.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2022-09-01, Elena Vance was appointed Chief Technology Officer.", "valid_from": "2022-09-01T00:00:00Z"}
        ]
    },
    {
        "query": "What programming language was used for backend microservices in 2019?",
        "expected_target": "Java 8 Spring",
        "invalid_outdated_target": "Python 3.11 FastAPI and Go",
        "valid_at": "2019-11-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2017-01-01, backend services were authored in Java 8 Spring.", "valid_from": "2017-01-01T00:00:00Z"},
            {"content": "In 2023-01-01, backend services transitioned to Python 3.11 FastAPI and Go.", "valid_from": "2023-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "What programming languages are used for backend microservices in 2024?",
        "expected_target": "Python 3.11 FastAPI and Go",
        "invalid_outdated_target": "Java 8 Spring",
        "valid_at": "2024-04-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2017-01-01, backend services were authored in Java 8 Spring.", "valid_from": "2017-01-01T00:00:00Z"},
            {"content": "In 2023-01-01, backend services transitioned to Python 3.11 FastAPI and Go.", "valid_from": "2023-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the log retention duration in 2021?",
        "expected_target": "7 days",
        "invalid_outdated_target": "90 days",
        "valid_at": "2021-08-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2020-01-01, log retention window was limited to 7 days.", "valid_from": "2020-01-01T00:00:00Z"},
            {"content": "In 2023-04-01, log retention policy was expanded to 90 days.", "valid_from": "2023-04-01T00:00:00Z"}
        ]
    },
    {
        "query": "What is the log retention duration in 2024?",
        "expected_target": "90 days",
        "invalid_outdated_target": "7 days",
        "valid_at": "2024-02-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2020-01-01, log retention window was limited to 7 days.", "valid_from": "2020-01-01T00:00:00Z"},
            {"content": "In 2023-04-01, log retention policy was expanded to 90 days.", "valid_from": "2023-04-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the primary monitoring tool in 2020?",
        "expected_target": "Nagios Core",
        "invalid_outdated_target": "Prometheus and Datadog",
        "valid_at": "2020-04-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2018-01-01, infrastructure alerts were routed through Nagios Core.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2022-03-01, observability was modernized with Prometheus and Datadog.", "valid_from": "2022-03-01T00:00:00Z"}
        ]
    },
    {
        "query": "What is the primary monitoring platform in 2024?",
        "expected_target": "Prometheus and Datadog",
        "invalid_outdated_target": "Nagios Core",
        "valid_at": "2024-03-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2018-01-01, infrastructure alerts were routed through Nagios Core.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2022-03-01, observability was modernized with Prometheus and Datadog.", "valid_from": "2022-03-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the production database in 2020?",
        "expected_target": "MySQL 5.7",
        "invalid_outdated_target": "PostgreSQL 16",
        "valid_at": "2020-06-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2017-01-01, all production records were stored in MySQL 5.7.", "valid_from": "2017-01-01T00:00:00Z"},
            {"content": "In 2023-05-01, production storage was upgraded to PostgreSQL 16.", "valid_from": "2023-05-01T00:00:00Z"}
        ]
    },
    {
        "query": "What is the production database in 2024?",
        "expected_target": "PostgreSQL 16",
        "invalid_outdated_target": "MySQL 5.7",
        "valid_at": "2024-05-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2017-01-01, all production records were stored in MySQL 5.7.", "valid_from": "2017-01-01T00:00:00Z"},
            {"content": "In 2023-05-01, production storage was upgraded to PostgreSQL 16.", "valid_from": "2023-05-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the office VPN solution in 2021?",
        "expected_target": "OpenVPN Access Server",
        "invalid_outdated_target": "Tailscale WireGuard Mesh",
        "valid_at": "2021-09-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2019-01-01, remote engineer access used OpenVPN Access Server.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "In 2023-02-01, corporate network access adopted Tailscale WireGuard Mesh.", "valid_from": "2023-02-01T00:00:00Z"}
        ]
    },
    {
        "query": "What is the corporate network access solution in 2024?",
        "expected_target": "Tailscale WireGuard Mesh",
        "invalid_outdated_target": "OpenVPN Access Server",
        "valid_at": "2024-03-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2019-01-01, remote engineer access used OpenVPN Access Server.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "In 2023-02-01, corporate network access adopted Tailscale WireGuard Mesh.", "valid_from": "2023-02-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the default analytics reporting currency in 2020?",
        "expected_target": "British Pounds GBP",
        "invalid_outdated_target": "US Dollars USD",
        "valid_at": "2020-04-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2018-01-01, executive financial reports standardized on British Pounds GBP.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2022-01-01, corporate accounting transitioned to US Dollars USD.", "valid_from": "2022-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "What is the default analytics reporting currency in 2024?",
        "expected_target": "US Dollars USD",
        "invalid_outdated_target": "British Pounds GBP",
        "valid_at": "2024-02-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2018-01-01, executive financial reports standardized on British Pounds GBP.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2022-01-01, corporate accounting transitioned to US Dollars USD.", "valid_from": "2022-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the internal wiki engine in 2020?",
        "expected_target": "MediaWiki self-hosted",
        "invalid_outdated_target": "Notion Enterprise workspace",
        "valid_at": "2020-09-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2018-01-01, internal company documentation was hosted on MediaWiki self-hosted.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2022-05-01, internal company documentation migrated to Notion Enterprise workspace.", "valid_from": "2022-05-01T00:00:00Z"}
        ]
    },
    {
        "query": "What is the internal documentation workspace in 2024?",
        "expected_target": "Notion Enterprise workspace",
        "invalid_outdated_target": "MediaWiki self-hosted",
        "valid_at": "2024-03-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2018-01-01, internal company documentation was hosted on MediaWiki self-hosted.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2022-05-01, internal company documentation migrated to Notion Enterprise workspace.", "valid_from": "2022-05-01T00:00:00Z"}
        ]
    },
    {
        "query": "Who was the designated Data Protection Officer in 2021?",
        "expected_target": "Clara Oswald",
        "invalid_outdated_target": "Alexander Wright",
        "valid_at": "2021-04-01T00:00:00Z",
        "facts_to_seed": [
            {"content": "In 2019-01-01, Clara Oswald was appointed Data Protection Officer.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "In 2023-01-01, Alexander Wright assumed the role of Data Protection Officer.", "valid_from": "2023-01-01T00:00:00Z"}
        ]
    },
]
add_category_cases("temporal", temporal_items)


# ==============================================================================
# Category 6: Historical (30 cases)
# Queries explicitly asking about past/superseded facts
# ==============================================================================
historical_items = [
    # dev (1-5)
    {
        "query": "What was the previous message queue prior to adopting Apache Kafka?",
        "expected_target": "ActiveMQ",
        "facts_to_seed": [
            {"content": "The original asynchronous message broker was ActiveMQ cluster.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2022-01-01, the messaging backbone migrated to Apache Kafka.", "valid_from": "2022-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "Where did Marcus work before joining the Core Infrastructure group?",
        "expected_target": "Apex Distributed Labs",
        "facts_to_seed": [
            {"content": "Marcus worked as systems researcher at Apex Distributed Labs in 2020.", "valid_from": "2020-01-01T00:00:00Z"},
            {"content": "In 2023-01-01, Marcus joined the Mnemos Core Infrastructure group.", "valid_from": "2023-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the legacy key-value store before migrating to Dragonfly?",
        "expected_target": "Redis 5 standalone",
        "facts_to_seed": [
            {"content": "The legacy key-value store was Redis 5 standalone prior to upgrade.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "In 2023-04-01, key-value storage upgraded to Dragonfly.", "valid_from": "2023-04-01T00:00:00Z"}
        ]
    },
    {
        "query": "Who held the position of Head of Security before Rachel Adams was hired?",
        "expected_target": "Gregory House",
        "facts_to_seed": [
            {"content": "Gregory House served as Head of Security until late 2021.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "Rachel Adams was hired as Head of Security in 2022-01-01.", "valid_from": "2022-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the initial vector index dimensionality tested during prototyping?",
        "expected_target": "128 dimensions",
        "facts_to_seed": [
            {"content": "The prototype vector index was evaluated with 128 dimensions.", "valid_from": "2021-01-01T00:00:00Z"},
            {"content": "In 2023-01-01, production vector embeddings standardized on 384 dimensions.", "valid_from": "2023-01-01T00:00:00Z"}
        ]
    },
    # test (6-30)
    {
        "query": "What was the previous corporate domain before mnemos.io was acquired?",
        "expected_target": "mnemos-project.org",
        "facts_to_seed": [
            {"content": "The initial public website was hosted at mnemos-project.org.", "valid_from": "2020-01-01T00:00:00Z"},
            {"content": "In 2023-08-01, all domains redirected to the new mnemos.io domain.", "valid_from": "2023-08-01T00:00:00Z"}
        ]
    },
    {
        "query": "What documentation framework was used prior to Starlight VitePress?",
        "expected_target": "Docusaurus v1",
        "facts_to_seed": [
            {"content": "Internal docs were originally rendered using Docusaurus v1.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "In 2023-02-01, documentation migrated to Starlight VitePress.", "valid_from": "2023-02-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the staging environment cluster region before moving to us-east-1?",
        "expected_target": "us-west-2",
        "facts_to_seed": [
            {"content": "Staging testing clusters were originally hosted in us-west-2 Oregon.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "In 2022-11-01, staging was consolidated into us-east-1 Virginia.", "valid_from": "2022-11-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the primary programming language for the original prototype engine?",
        "expected_target": "Rust 2018",
        "facts_to_seed": [
            {"content": "The v0 prototype kernel was built using Rust 2018 edition.", "valid_from": "2020-01-01T00:00:00Z"},
            {"content": "In 2022-05-01, the core engine was rewritten in Python with C-extensions.", "valid_from": "2022-05-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the previous container orchestration tool before Kubernetes?",
        "expected_target": "Docker Swarm",
        "facts_to_seed": [
            {"content": "Container instances were deployed using Docker Swarm cluster.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2021-06-01, workload scheduling moved entirely to Kubernetes.", "valid_from": "2021-06-01T00:00:00Z"}
        ]
    },
    {
        "query": "Who served as lead frontend engineer before Carlos Mendez joined?",
        "expected_target": "Rebecca Ferguson",
        "facts_to_seed": [
            {"content": "Rebecca Ferguson was lead frontend engineer between 2020 and 2022.", "valid_from": "2020-01-01T00:00:00Z"},
            {"content": "Carlos Mendez assumed lead frontend architecture duties in 2023.", "valid_from": "2023-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the previous secret management solution before HashiCorp Vault?",
        "expected_target": "AWS Secrets Manager",
        "facts_to_seed": [
            {"content": "Credentials were historically stored in AWS Secrets Manager.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "In 2023-03-01, secret management standardized on HashiCorp Vault.", "valid_from": "2023-03-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the earlier database migration utility before Alembic?",
        "expected_target": "Flyway Java",
        "facts_to_seed": [
            {"content": "Schema evolution was managed by Flyway Java runner.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2022-01-01, migrations were re-implemented natively using Alembic.", "valid_from": "2022-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the previous authentication mechanism for internal tools?",
        "expected_target": "HTTP Basic Auth with htpasswd",
        "facts_to_seed": [
            {"content": "Internal administrative routes used HTTP Basic Auth with htpasswd.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "In 2022-07-01, internal access mandated Okta SAML SSO.", "valid_from": "2022-07-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the original cloud storage provider before Cloudflare R2?",
        "expected_target": "AWS S3 Standard",
        "facts_to_seed": [
            {"content": "Object storage was previously provisioned in AWS S3 Standard buckets.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "In 2023-04-01, storage moved to Cloudflare R2 to eliminate egress costs.", "valid_from": "2023-04-01T00:00:00Z"}
        ]
    },
    {
        "query": "Who directed the Machine Learning division before Dr. Simon Gray?",
        "expected_target": "Dr. Ronald Evans",
        "facts_to_seed": [
            {"content": "Dr. Ronald Evans directed the ML division until 2021.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "Dr. Simon Gray took over as ML Director in 2022-01-01.", "valid_from": "2022-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the legacy load balancer software before Envoy?",
        "expected_target": "Nginx Open Source",
        "facts_to_seed": [
            {"content": "Ingress reverse proxying was handled by Nginx Open Source.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2022-09-01, edge routing was replaced by Envoy proxy.", "valid_from": "2022-09-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the previous git repository hosting service before GitHub Enterprise?",
        "expected_target": "GitLab Self-Hosted",
        "facts_to_seed": [
            {"content": "Source code was previously hosted on a GitLab Self-Hosted instance.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2022-04-01, repositories migrated to GitHub Enterprise Cloud.", "valid_from": "2022-04-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the initial embedding model evaluated before bge-small-en?",
        "expected_target": "all-MiniLM-L6-v2",
        "facts_to_seed": [
            {"content": "The prototype vector retrieval evaluated all-MiniLM-L6-v2 embeddings.", "valid_from": "2021-01-01T00:00:00Z"},
            {"content": "In 2023-06-01, embeddings transitioned to bge-small-en-v1.5.", "valid_from": "2023-06-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the old internal communications tool before Slack?",
        "expected_target": "Mattermost",
        "facts_to_seed": [
            {"content": "Engineering team chat was originally hosted on Mattermost server.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "In 2022-08-01, the organization migrated to Slack Enterprise Grid.", "valid_from": "2022-08-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the former incident response ticketing system before PagerDuty?",
        "expected_target": "Opsgenie",
        "facts_to_seed": [
            {"content": "On-call on-call alerting was handled by Opsgenie.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "In 2023-01-01, incident management consolidated into PagerDuty.", "valid_from": "2023-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the predecessor to the current Mnemos Python SDK?",
        "expected_target": "mnemos-client-legacy",
        "facts_to_seed": [
            {"content": "The original Python interface was published as mnemos-client-legacy package.", "valid_from": "2021-01-01T00:00:00Z"},
            {"content": "In 2023-09-01, the unified mnemos SDK was released.", "valid_from": "2023-09-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the early database replication strategy before logical replication?",
        "expected_target": "pg_dump nightly snapshotting",
        "facts_to_seed": [
            {"content": "Database backups were created using pg_dump nightly snapshotting.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2022-03-01, database sync upgraded to PostgreSQL logical replication.", "valid_from": "2022-03-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the previous memory allocation per container before 4GB?",
        "expected_target": "512MB RAM",
        "facts_to_seed": [
            {"content": "API pods were historically capped at 512MB RAM.", "valid_from": "2020-01-01T00:00:00Z"},
            {"content": "In 2023-05-01, API container memory limits were raised to 4GB RAM.", "valid_from": "2023-05-01T00:00:00Z"}
        ]
    },
    {
        "query": "Where was the company holiday retreat held in 2019?",
        "expected_target": "Lake Tahoe",
        "facts_to_seed": [
            {"content": "The 2019 company annual retreat was hosted in Lake Tahoe.", "valid_from": "2019-12-01T00:00:00Z"},
            {"content": "The 2023 company retreat took place in Costa Rica.", "valid_from": "2023-12-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the previous static asset CDN provider before Cloudflare?",
        "expected_target": "Fastly CDN",
        "facts_to_seed": [
            {"content": "Static assets were previously delivered via Fastly CDN edges.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "In 2022-09-01, static caching migrated to Cloudflare Enterprise.", "valid_from": "2022-09-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the earlier code review guideline tool before Danger JS?",
        "expected_target": "Reviewdog",
        "facts_to_seed": [
            {"content": "Automated pull request linting was historically performed by Reviewdog.", "valid_from": "2020-01-01T00:00:00Z"},
            {"content": "In 2023-01-01, PR validation shifted to Danger JS custom rules.", "valid_from": "2023-01-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the initial database connection pooler before PgBouncer?",
        "expected_target": "pgpool-II",
        "facts_to_seed": [
            {"content": "Database client connections were originally balanced using pgpool-II.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2021-10-01, connection pooling standardized on PgBouncer.", "valid_from": "2021-10-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the predecessor API serialization library before Pydantic v2?",
        "expected_target": "Marshmallow schemas",
        "facts_to_seed": [
            {"content": "API request validation was originally handled using Marshmallow schemas.", "valid_from": "2019-01-01T00:00:00Z"},
            {"content": "In 2023-06-01, data models were rewritten with high speed Pydantic v2.", "valid_from": "2023-06-01T00:00:00Z"}
        ]
    },
    {
        "query": "What was the old internal domain registrar before Cloudflare Registrar?",
        "expected_target": "Namecheap",
        "facts_to_seed": [
            {"content": "Corporate top-level domains were historically purchased through Namecheap.", "valid_from": "2018-01-01T00:00:00Z"},
            {"content": "In 2022-03-01, all domain management was transferred to Cloudflare Registrar.", "valid_from": "2022-03-01T00:00:00Z"}
        ]
    },
]
add_category_cases("historical", historical_items)


# ==============================================================================
# Category 7: Contradictory Fact (30 cases)
# Handling conflicting facts / updates with recency or confidence resolution
# ==============================================================================
contradictory_items = [
    # dev (1-5)
    {
        "query": "What is the confirmed throughput capacity of the primary ingestion gateway?",
        "expected_target": "50,000 events/sec",
        "invalid_outdated_target": "10,000 events/sec",
        "facts_to_seed": [
            {"content": "Preliminary benchmarks estimated ingestion gateway capacity at 10,000 events/sec.", "valid_from": "2022-01-01T00:00:00Z", "confidence": 0.5},
            {"content": "Final stress tests confirmed primary ingestion gateway capacity reaches 50,000 events/sec.", "valid_from": "2023-06-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the true packet drop rate on spine switch 04?",
        "expected_target": "0.001%",
        "invalid_outdated_target": "14.2%",
        "facts_to_seed": [
            {"content": "Faulty sensor reported severe packet drop rate of 14.2% on spine switch 04.", "valid_from": "2023-01-01T00:00:00Z", "confidence": 0.4},
            {"content": "Calibrated diagnostic probes verified actual packet drop rate on spine switch 04 is 0.001%.", "valid_from": "2023-01-02T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the production database replica count in eu-west-1?",
        "expected_target": "5 read replicas",
        "invalid_outdated_target": "2 read replicas",
        "facts_to_seed": [
            {"content": "Infrastructure draft proposed 2 read replicas in eu-west-1.", "valid_from": "2022-05-01T00:00:00Z", "confidence": 0.6},
            {"content": "Production deployment provisioned 5 read replicas in eu-west-1 for high availability.", "valid_from": "2023-01-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the validated AES encryption key size for tenant volumes?",
        "expected_target": "AES-256-GCM",
        "invalid_outdated_target": "AES-128-CBC",
        "facts_to_seed": [
            {"content": "Draft specification mentioned AES-128-CBC encryption.", "valid_from": "2021-01-01T00:00:00Z", "confidence": 0.4},
            {"content": "Final security audit verified all tenant volumes enforce AES-256-GCM encryption.", "valid_from": "2022-08-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the active Redis maxmemory eviction policy?",
        "expected_target": "volatile-lru",
        "invalid_outdated_target": "noeviction",
        "facts_to_seed": [
            {"content": "Temporary hotfix configured Redis with noeviction policy.", "valid_from": "2022-03-01T00:00:00Z", "confidence": 0.5},
            {"content": "Permanent cluster configuration established volatile-lru eviction policy.", "valid_from": "2022-09-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    # test (6-30)
    {
        "query": "What was the actual cause of the December database freeze?",
        "expected_target": "disk IOPS exhaustion",
        "invalid_outdated_target": "CPU deadlock",
        "facts_to_seed": [
            {"content": "Initial incident hypothesis blamed CPU deadlock for the December database freeze.", "valid_from": "2023-12-01T00:00:00Z", "confidence": 0.4},
            {"content": "Root cause analysis proved the December database freeze was caused by disk IOPS exhaustion.", "valid_from": "2023-12-05T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the active maximum worker concurrency setting?",
        "expected_target": "128 threads",
        "invalid_outdated_target": "32 threads",
        "facts_to_seed": [
            {"content": "Legacy configuration limited worker concurrency to 32 threads.", "valid_from": "2021-01-01T00:00:00Z", "confidence": 0.5},
            {"content": "Updated high-throughput tuning expanded worker concurrency to 128 threads.", "valid_from": "2023-01-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "Who is the designated project lead for Project Valkyrie?",
        "expected_target": "Samantha Reed",
        "invalid_outdated_target": "Jack Peterson",
        "facts_to_seed": [
            {"content": "Jack Peterson was initially announced as lead for Project Valkyrie.", "valid_from": "2023-01-01T00:00:00Z", "confidence": 0.4},
            {"content": "Executive leadership formally appointed Samantha Reed as project lead for Project Valkyrie.", "valid_from": "2023-02-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the confirmed round-trip latency across the transatlantic link?",
        "expected_target": "68 milliseconds",
        "invalid_outdated_target": "145 milliseconds",
        "facts_to_seed": [
            {"content": "Ping test during fiber maintenance recorded transatlantic latency of 145 milliseconds.", "valid_from": "2023-04-01T00:00:00Z", "confidence": 0.5},
            {"content": "Optimized submarine cable routing confirmed regular transatlantic round-trip latency is 68 milliseconds.", "valid_from": "2023-04-10T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the validated SSL certificate expiration date for api.mnemos.io?",
        "expected_target": "November 2026",
        "invalid_outdated_target": "March 2024",
        "facts_to_seed": [
            {"content": "Previous certificate for api.mnemos.io was scheduled to expire in March 2024.", "valid_from": "2023-01-01T00:00:00Z", "confidence": 0.5},
            {"content": "Automated certbot renewal issued wildcard TLS certificates valid through November 2026.", "valid_from": "2024-01-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the actual maximum memory limit for graph worker pods?",
        "expected_target": "16 Gigabytes",
        "invalid_outdated_target": "2 Gigabytes",
        "facts_to_seed": [
            {"content": "Initial Helm chart set graph worker memory limit to 2 Gigabytes.", "valid_from": "2022-01-01T00:00:00Z", "confidence": 0.5},
            {"content": "Production chart release adjusted graph worker memory limit to 16 Gigabytes.", "valid_from": "2023-01-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the verified uptime SLA committed in enterprise contracts?",
        "expected_target": "99.95%",
        "invalid_outdated_target": "99.0%",
        "facts_to_seed": [
            {"content": "Draft terms of service stated an availability target of 99.0%.", "valid_from": "2021-01-01T00:00:00Z", "confidence": 0.4},
            {"content": "Standard enterprise master service agreements guarantee an uptime SLA of 99.95%.", "valid_from": "2023-01-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the active maximum query result limit in the API?",
        "expected_target": "100 records",
        "invalid_outdated_target": "10 records",
        "facts_to_seed": [
            {"content": "Beta release restricted API search result limit to 10 records.", "valid_from": "2022-01-01T00:00:00Z", "confidence": 0.5},
            {"content": "General availability API expands maximum query result limit to 100 records.", "valid_from": "2023-01-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the confirmed IP address of the primary DNS resolver?",
        "expected_target": "10.0.0.53",
        "invalid_outdated_target": "192.168.1.1",
        "facts_to_seed": [
            {"content": "Local developer setup pointed DNS to gateway 192.168.1.1.", "valid_from": "2021-01-01T00:00:00Z", "confidence": 0.4},
            {"content": "Corporate internal VPC infrastructure designates 10.0.0.53 as the primary DNS resolver.", "valid_from": "2022-06-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the active HTTP keepalive timeout value?",
        "expected_target": "65 seconds",
        "invalid_outdated_target": "5 seconds",
        "facts_to_seed": [
            {"content": "Default web server template specified keepalive timeout of 5 seconds.", "valid_from": "2022-01-01T00:00:00Z", "confidence": 0.5},
            {"content": "High performance edge reverse proxy standardizes HTTP keepalive timeout at 65 seconds.", "valid_from": "2023-01-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the verified total size of the seed dataset?",
        "expected_target": "1.2 Million embeddings",
        "invalid_outdated_target": "50,000 embeddings",
        "facts_to_seed": [
            {"content": "Preliminary benchmark corpus contained only 50,000 embeddings.", "valid_from": "2022-01-01T00:00:00Z", "confidence": 0.5},
            {"content": "Full scale corporate benchmark corpus indexes 1.2 Million embeddings.", "valid_from": "2023-01-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the active database checkpoint timeout interval?",
        "expected_target": "15 minutes",
        "invalid_outdated_target": "2 minutes",
        "facts_to_seed": [
            {"content": "Test environment used aggressive database checkpoint timeout of 2 minutes.", "valid_from": "2021-01-01T00:00:00Z", "confidence": 0.5},
            {"content": "Production PostgreSQL cluster enforces checkpoint_timeout of 15 minutes.", "valid_from": "2023-01-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "Who is the certified compliance officer for HIPAA audits?",
        "expected_target": "Beatrice Potter",
        "invalid_outdated_target": "Thomas Sterling",
        "facts_to_seed": [
            {"content": "Thomas Sterling handled early HIPAA compliance reviews.", "valid_from": "2021-01-01T00:00:00Z", "confidence": 0.4},
            {"content": "Beatrice Potter was certified and appointed as designated HIPAA Compliance Officer.", "valid_from": "2022-08-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the confirmed vector dimension of the text embeddings?",
        "expected_target": "384-dimensional",
        "invalid_outdated_target": "1536-dimensional",
        "facts_to_seed": [
            {"content": "Early experimentation considered 1536-dimensional OpenAI embeddings.", "valid_from": "2022-01-01T00:00:00Z", "confidence": 0.5},
            {"content": "Production Mnemos architecture standardized on 384-dimensional FastEmbed vectors.", "valid_from": "2023-01-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the active batch size for background vector indexing?",
        "expected_target": "256 items",
        "invalid_outdated_target": "16 items",
        "facts_to_seed": [
            {"content": "Development script defaulted batch size to 16 items.", "valid_from": "2022-01-01T00:00:00Z", "confidence": 0.5},
            {"content": "Production background indexer tunes ingestion batch size to 256 items.", "valid_from": "2023-01-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the official minimum password length for staff accounts?",
        "expected_target": "16 characters",
        "invalid_outdated_target": "8 characters",
        "facts_to_seed": [
            {"content": "Old security handbook required minimum password length of 8 characters.", "valid_from": "2019-01-01T00:00:00Z", "confidence": 0.4},
            {"content": "Current infosec policy strictly mandates 16 characters with hardware MFA.", "valid_from": "2022-10-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the active maximum retry count on failed webhook deliveries?",
        "expected_target": "5 retry attempts",
        "invalid_outdated_target": "1 retry attempt",
        "facts_to_seed": [
            {"content": "Initial webhook dispatcher attempted only 1 retry attempt before dropping.", "valid_from": "2021-01-01T00:00:00Z", "confidence": 0.5},
            {"content": "Resilient webhook dispatcher implements exponential backoff with 5 retry attempts.", "valid_from": "2022-07-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the confirmed retention policy for customer audit logs?",
        "expected_target": "7 years",
        "invalid_outdated_target": "30 days",
        "facts_to_seed": [
            {"content": "Preliminary draft proposed keeping audit logs for 30 days.", "valid_from": "2020-01-01T00:00:00Z", "confidence": 0.4},
            {"content": "Regulatory compliance mandates retaining all immutable customer audit logs for 7 years.", "valid_from": "2021-06-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the primary cloud region for disaster recovery failover?",
        "expected_target": "eu-central-1 Frankfurt",
        "invalid_outdated_target": "ap-southeast-1 Singapore",
        "facts_to_seed": [
            {"content": "Initial disaster recovery plan selected ap-southeast-1 Singapore as secondary.", "valid_from": "2021-01-01T00:00:00Z", "confidence": 0.5},
            {"content": "Revised global DR plan established cold standby replication in eu-central-1 Frankfurt.", "valid_from": "2022-11-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the verified maximum execution timeout for API requests?",
        "expected_target": "30 seconds",
        "invalid_outdated_target": "120 seconds",
        "facts_to_seed": [
            {"content": "Legacy gateway allowed long-running requests to persist for 120 seconds.", "valid_from": "2020-01-01T00:00:00Z", "confidence": 0.5},
            {"content": "Production API gateway enforces a strict global request timeout of 30 seconds.", "valid_from": "2022-05-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the confirmed minimum healthy host count in the API load pool?",
        "expected_target": "3 healthy instances",
        "invalid_outdated_target": "1 healthy instance",
        "facts_to_seed": [
            {"content": "Initial auto-healing rules allowed load pool to drop to 1 healthy instance.", "valid_from": "2021-01-01T00:00:00Z", "confidence": 0.5},
            {"content": "Revised reliability policy mandates maintaining at least 3 healthy instances in the API load pool.", "valid_from": "2022-09-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the validated database connection timeout threshold?",
        "expected_target": "5000 milliseconds",
        "invalid_outdated_target": "60000 milliseconds",
        "facts_to_seed": [
            {"content": "Legacy connection pool allowed queries to hang for 60000 milliseconds before timeout.", "valid_from": "2020-01-01T00:00:00Z", "confidence": 0.4},
            {"content": "Updated database client driver sets a fail-fast timeout of 5000 milliseconds.", "valid_from": "2022-12-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the confirmed maximum allowed HTTP payload size?",
        "expected_target": "10 Megabytes",
        "invalid_outdated_target": "100 Megabytes",
        "facts_to_seed": [
            {"content": "Draft API documentation listed maximum upload payload size as 100 Megabytes.", "valid_from": "2021-01-01T00:00:00Z", "confidence": 0.5},
            {"content": "Production ingress WAF enforces a strict payload cap of 10 Megabytes.", "valid_from": "2022-06-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the verified daily backup schedule time?",
        "expected_target": "03:00 UTC",
        "invalid_outdated_target": "12:00 UTC",
        "facts_to_seed": [
            {"content": "Earlier cron table triggered daily database snapshots at 12:00 UTC during peak traffic.", "valid_from": "2020-01-01T00:00:00Z", "confidence": 0.4},
            {"content": "Adjusted backup schedule runs automated daily database snapshots at 03:00 UTC off-peak.", "valid_from": "2022-03-01T00:00:00Z", "confidence": 1.0}
        ]
    },
    {
        "query": "What is the verified production Redis cluster shard count?",
        "expected_target": "6 master shards",
        "invalid_outdated_target": "2 master shards",
        "facts_to_seed": [
            {"content": "Staging Redis topology ran with 2 master shards.", "valid_from": "2021-01-01T00:00:00Z", "confidence": 0.5},
            {"content": "Production Redis deployment scales across 6 master shards with replica pairs.", "valid_from": "2023-01-01T00:00:00Z", "confidence": 1.0}
        ]
    },
]
add_category_cases("contradictory_fact", contradictory_items)


# ==============================================================================
# Category 8: Paraphrased (30 cases)
# Radically rephrased queries testing semantic invariance with minimal token overlap
# ==============================================================================
paraphrased_items = [
    # dev (1-5)
    {
        "query": "At what thermal ceiling does the processor intentionally downgrade clock speed to prevent physical burn?",
        "expected_target": "95 degrees Celsius",
        "facts_to_seed": [{"content": "The automated thermal mitigation daemon initiates CPU throttling at 95 degrees Celsius."}]
    },
    {
        "query": "What method guarantees that concurrent database writes do not produce corrupted intermediate views?",
        "expected_target": "Serializable Snapshot Isolation",
        "facts_to_seed": [{"content": "Transaction consistency across high contention mutations relies on Serializable Snapshot Isolation."}]
    },
    {
        "query": "Where are discarded customer files permanently shredded in adherence to the right to be forgotten?",
        "expected_target": "Cryptographic Erasure Vault",
        "facts_to_seed": [{"content": "User account purging executes automated zero-fill shredding inside the Cryptographic Erasure Vault."}]
    },
    {
        "query": "What mathematical construct calculates the likelihood of an entity transition in the knowledge graph?",
        "expected_target": "Markov Transition Matrix",
        "facts_to_seed": [{"content": "Probabilistic edge traversal between entities is parameterized by a continuous Markov Transition Matrix."}]
    },
    {
        "query": "How is incoming traffic evenly dispersed during sudden demand surges to avert backend brownouts?",
        "expected_target": "Leaky Bucket Rate Limiting",
        "facts_to_seed": [{"content": "Edge gateways absorb client traffic spikes by applying distributed Leaky Bucket Rate Limiting."}]
    },
    # test (6-30)
    {
        "query": "Which software component acts as the supreme arbitrator when consensus cannot be reached among storage nodes?",
        "expected_target": "Chubby Lock Service",
        "facts_to_seed": [{"content": "Split-brain cluster reconciliation yields authority to the distributed Chubby Lock Service."}]
    },
    {
        "query": "What defensive barrier halts unauthorized lateral movement following an ingress breach?",
        "expected_target": "Microsegmentation Firewalls",
        "facts_to_seed": [{"content": "Zero-trust internal packet routing is physically bounded by Microsegmentation Firewalls."}]
    },
    {
        "query": "Which machine learning approach compresses cumbersome neural networks into nimble edge artifacts?",
        "expected_target": "Knowledge Distillation",
        "facts_to_seed": [{"content": "Large language teacher models transfer reasoning capabilities to compact student models via Knowledge Distillation."}]
    },
    {
        "query": "What mechanism allows asynchronous workers to resume computation precisely where they left off after sudden termination?",
        "expected_target": "Durable Checkpointing",
        "facts_to_seed": [{"content": "Worker process state recovery across sudden spot instance interruptions relies on Durable Checkpointing."}]
    },
    {
        "query": "What paradigm permits instantaneous zero-copy duplication of multi-terabyte dataset snapshots?",
        "expected_target": "Copy-on-Write B-Trees",
        "facts_to_seed": [{"content": "Instantaneous database cloning leverages storage blocks managed by Copy-on-Write B-Trees."}]
    },
    {
        "query": "What cryptographic primitive enables proof of authentication without ever transmitting the secret passkey?",
        "expected_target": "Zero-Knowledge SNARKs",
        "facts_to_seed": [{"content": "Identity verification protocols allow passwordless proof through non-interactive Zero-Knowledge SNARKs."}]
    },
    {
        "query": "How do distributed clocks reach synchronized time agreement across geographically separated continents?",
        "expected_target": "TrueTime Atomic Clocks",
        "facts_to_seed": [{"content": "Inter-datacenter timestamp alignment is bounded by GPS receivers and TrueTime Atomic Clocks."}]
    },
    {
        "query": "What architectural trick enables continuous database querying without holding table-level locks?",
        "expected_target": "Multi-Version Concurrency Control",
        "facts_to_seed": [{"content": "Non-blocking parallel reads and writes operate seamlessly through Multi-Version Concurrency Control."}]
    },
    {
        "query": "What statistical structure rapidly filters out non-existent keys before querying physical storage disks?",
        "expected_target": "Counting Bloom Filter",
        "facts_to_seed": [{"content": "Point lookup latency is saved by verifying presence via an in-memory Counting Bloom Filter."}]
    },
    {
        "query": "What routine reclaims unused memory allocations to prevent runaway memory expansion?",
        "expected_target": "Generational Garbage Collector",
        "facts_to_seed": [{"content": "Dormant heap allocations are periodically identified and freed by the Generational Garbage Collector."}]
    },
    {
        "query": "What mechanism ensures that multiple identical webhook submissions execute state alterations exactly once?",
        "expected_target": "Deterministic Idempotency Hash",
        "facts_to_seed": [{"content": "Duplicate event suppression validates request signatures using a Deterministic Idempotency Hash."}]
    },
    {
        "query": "How are volatile network sockets smoothly transferred between container instances without severing connections?",
        "expected_target": "SO_REUSEPORT Socket Handoff",
        "facts_to_seed": [{"content": "Zero-downtime proxy binary updates transfer live TCP file descriptors via SO_REUSEPORT Socket Handoff."}]
    },
    {
        "query": "What numerical score ranks the topological importance of nodes within the historical entity web?",
        "expected_target": "Eigenvector Centrality",
        "facts_to_seed": [{"content": "Entity relevance across graph relationships is weighted according to calculated Eigenvector Centrality."}]
    },
    {
        "query": "What format encapsulates cold database backups to withstand bit rot over decades of deep storage?",
        "expected_target": "Parquet with Reed-Solomon Parity",
        "facts_to_seed": [{"content": "Archival data longevity against hardware degradation is safeguarded by Parquet with Reed-Solomon Parity."}]
    },
    {
        "query": "What protocol prevents malicious middle-men from spoofing DNS query resolutions?",
        "expected_target": "DNSSEC Cryptographic Signatures",
        "facts_to_seed": [{"content": "Domain resolution authenticity is cryptographically guaranteed through DNSSEC Cryptographic Signatures."}]
    },
    {
        "query": "What scheduling policy guarantees that low-priority background maintenance does not starve mission-critical traffic?",
        "expected_target": "Deficit Weighted Round Robin",
        "facts_to_seed": [{"content": "Ingress queue dispatch fairness across disparate tenant classes enforces Deficit Weighted Round Robin."}]
    },
    {
        "query": "How is high availability preserved when the master coordinator node experiences sudden power loss?",
        "expected_target": "Automated Leader Failover",
        "facts_to_seed": [{"content": "Cluster continuity during master node outages is achieved through split-second Automated Leader Failover."}]
    },
    {
        "query": "What security wrapper isolates untrusted foreign code execution inside micro-virtual machines?",
        "expected_target": "Firecracker Jailer",
        "facts_to_seed": [{"content": "Tenant custom code execution sandboxes are secured against escape by the Firecracker Jailer."}]
    },
    {
        "query": "What technique condenses sparse high-dimensional entity graphs into dense continuous vector representations?",
        "expected_target": "Node2Vec Random Walks",
        "facts_to_seed": [{"content": "Structural graph topological embeddings are learned using biased second-order Node2Vec Random Walks."}]
    },
    {
        "query": "What method enables instant rollback of schema migrations when unexpected runtime anomalies emerge?",
        "expected_target": "Expand-and-Contract Evolution",
        "facts_to_seed": [{"content": "Zero-risk relational database structural refactorings employ the Expand-and-Contract Evolution pattern."}]
    },
    {
        "query": "How are corrupted bit flips in storage sectors automatically repaired without manual sysadmin intervention?",
        "expected_target": "Scrubbing with Reed-Solomon Codecs",
        "facts_to_seed": [{"content": "Background filesystem integrity auditing performs silent bit rot restoration through Scrubbing with Reed-Solomon Codecs."}]
    },
    {
        "query": "What algorithm determines which cached assets get thrown out when solid-state drives become full?",
        "expected_target": "Adaptive Replacement Cache",
        "facts_to_seed": [{"content": "Dynamic page eviction balancing recency and frequency utilizes the Adaptive Replacement Cache."}]
    },
    {
        "query": "What strategy allows client applications to survive temporary outages by recording modifications on the device?",
        "expected_target": "Conflict-Free Replicated Data Types",
        "facts_to_seed": [{"content": "Offline-first mobile reconciliation merges asynchronous mutations through Conflict-Free Replicated Data Types."}]
    },
    {
        "query": "What runtime supervisor revives crashed microservice worker processes within milliseconds?",
        "expected_target": "Erlang-Style Supervisor Tree",
        "facts_to_seed": [{"content": "Fault isolation and rapid thread recovery are governed by an Erlang-Style Supervisor Tree."}]
    },
    {
        "query": "What cryptographic certificate protects domain communications from quantum computer decryption?",
        "expected_target": "Falcon Lattice Signatures",
        "facts_to_seed": [{"content": "Post-quantum transport security verifies identity certificates signed with Falcon Lattice Signatures."}]
    },
]
add_category_cases("paraphrased", paraphrased_items)

# Write output dataset
dataset_path = "benchmarks/datasets/retrieval_benchmark_240.json"
os.makedirs(os.path.dirname(dataset_path), exist_ok=True)
with open(dataset_path, "w", encoding="utf-8") as f:
    json.dump(cases, f, indent=2)

# Also write to temporal_qa.json for backward compatibility
compat_path = "benchmarks/datasets/temporal_qa.json"
with open(compat_path, "w", encoding="utf-8") as f:
    json.dump(cases, f, indent=2)

print(f"Successfully generated {len(cases)} benchmark test cases across 8 categories in '{dataset_path}'")
dev_count = sum(1 for c in cases if c["split"] == "dev")
test_count = sum(1 for c in cases if c["split"] == "test")
print(f"Split breakdown: {dev_count} development queries, {test_count} held-out test queries.")

by_cat = {}
for c in cases:
    cat = c["category"]
    by_cat[cat] = by_cat.get(cat, {"dev": 0, "test": 0})
    by_cat[cat][c["split"]] += 1

for cat, counts in sorted(by_cat.items()):
    print(f"  - {cat:<20}: {counts['dev']} dev, {counts['test']} test (total {counts['dev'] + counts['test']})")

"""Generate a comprehensive 100-query benchmark dataset covering 5 core memory categories."""
import json
import os

cases = []

# ==============================================================================
# Category 1: Semantic Memory Retrieval (20 cases: sem_01 to sem_20)
# Testing semantic comprehension, paraphrasing, and conceptual retrieval
# ==============================================================================
semantic_seeds = [
    (
        "sem_01",
        "Who specializes in quantum-resistant cryptography?",
        "David",
        "David is a principal researcher in post-quantum lattice-based encryption algorithms."
    ),
    (
        "sem_02",
        "What caused the failure of the Orion computing cluster?",
        "memory saturation",
        "The Orion computing infrastructure crashed due to severe memory saturation and OOM kills."
    ),
    (
        "sem_03",
        "Who filed patents for brain-inspired neuromorphic chips?",
        "Elena",
        "Elena authored three foundational patents on neuromorphic hardware accelerators."
    ),
    (
        "sem_04",
        "What authentication protocol is mandatory for internal microservices?",
        "mutual TLS",
        "All microservice traffic must enforce zero-trust mutual TLS with automated rotation."
    ),
    (
        "sem_05",
        "Which machine learning technique optimizes LLM inference latency?",
        "speculative decoding",
        "Inference acceleration is achieved by leveraging speculative decoding with draft models."
    ),
    (
        "sem_06",
        "Who leads the incident response team during security breaches?",
        "Rachel",
        "Rachel serves as commander for critical cybersecurity incidents and breach containment."
    ),
    (
        "sem_07",
        "What protocol governs the distributed consensus in the storage tier?",
        "Raft",
        "Distributed state synchronization across storage nodes relies on the Raft protocol."
    ),
    (
        "sem_08",
        "Which compression algorithm was chosen for cold data archival?",
        "Zstandard",
        "Historical log archives are compacted using the Zstandard compression standard level 19."
    ),
    (
        "sem_09",
        "Who manages the developer productivity and CI platform?",
        "Victor",
        "Victor orchestrates engineering workflow toolchains and internal developer infrastructure."
    ),
    (
        "sem_10",
        "What mechanism protects against cascade failures in external API calls?",
        "circuit breakers",
        "Outbound network calls to external payment vendors are guarded by automated circuit breakers."
    ),
    (
        "sem_11",
        "Who conducted the benchmark analysis on vector indexing performance?",
        "Marcus",
        "Marcus executed extensive empirical evaluations on HNSW graph construction and recall."
    ),
    (
        "sem_12",
        "What strategy is used to prevent hot partitions in distributed caching?",
        "consistent hashing",
        "Cache key distribution employs consistent hashing with virtual nodes to eliminate hot spots."
    ),
    (
        "sem_13",
        "Who drafted the technical RFC for the streaming data ingestion pipeline?",
        "Sophia",
        "Sophia formulated the formal design RFC for high-throughput real-time stream ingestion."
    ),
    (
        "sem_14",
        "What metric dictates auto-scaling thresholds for the worker fleet?",
        "queue depth",
        "Horizontal autoscaling triggers are driven by asynchronous job queue depth and lag."
    ),
    (
        "sem_15",
        "Who is responsible for international regulatory compliance and privacy?",
        "Alexander",
        "Alexander oversees global data sovereignty, GDPR audits, and privacy governance."
    ),
    (
        "sem_16",
        "Which format is adopted for cross-language RPC serialization?",
        "Protocol Buffers",
        "Internal service boundaries serialize inter-process messages using Protocol Buffers."
    ),
    (
        "sem_17",
        "Who designed the zero-downtime database migration framework?",
        "Leila",
        "Leila engineered the expandable-contract schema evolution framework for continuous uptime."
    ),
    (
        "sem_18",
        "What caching topology provides local low-latency reads for edge nodes?",
        "read-through replica",
        "Edge regions utilize an in-memory read-through replica cache backed by invalidation webhooks."
    ),
    (
        "sem_19",
        "Who conducts threat modeling for cloud infrastructure security?",
        "Nathan",
        "Nathan performs automated vulnerability scans and adversarial threat simulations on Kubernetes."
    ),
    (
        "sem_20",
        "What method ensures deterministic builds across developer environments?",
        "Hermetic containers",
        "Hermetic containers with pinned SHA-256 toolchain digests guarantee reproducible artifacts."
    ),
]

for cid, query, target, content in semantic_seeds:
    cases.append({
        "id": cid,
        "category": "semantic_retrieval",
        "query": query,
        "expected_target": target,
        "invalid_outdated_target": None,
        "valid_at": None,
        "facts_to_seed": [
            {
                "content": content,
                "valid_from": "2024-01-01T00:00:00Z",
                "confidence": 1.0,
            }
        ]
    })

# ==============================================================================
# Category 2: Historical & Temporal Queries (20 cases: hist_01 to hist_20)
# Testing point-in-time validity [valid_from, valid_to) at past timestamps
# ==============================================================================
historical_scenarios = [
    # Person, past_org, past_date, new_org, new_date, query_date, past_query, past_target, new_query, new_target
    ("Sarah", "Solaris", "2022-01-01", "Horizon", "2024-01-01", "2023-06-01", "Where did Sarah work in June 2023?", "Solaris", "Where did Sarah work in March 2024?", "Horizon"),
    ("Carlos", "Datadog", "2021-03-01", "Cloudflare", "2023-09-01", "2022-08-01", "Where was Carlos employed in August 2022?", "Datadog", "Where was Carlos employed in December 2023?", "Cloudflare"),
    ("Maya", "Berlin", "2022-05-01", "Singapore", "2024-02-01", "2023-03-01", "Where did Maya live in March 2023?", "Berlin", "Where did Maya live in May 2024?", "Singapore"),
    ("Julian", "Stripe", "2020-01-01", "OpenAI", "2023-11-01", "2022-04-01", "Where was Julian working in April 2022?", "Stripe", "Where was Julian working in January 2024?", "OpenAI"),
    ("Fiona", "Seattle", "2021-06-01", "London", "2023-07-01", "2022-10-01", "Where was Fiona located in October 2022?", "Seattle", "Where was Fiona located in November 2023?", "London"),
    ("Liam", "Anthropic", "2022-02-01", "DeepMind", "2024-04-01", "2023-07-01", "Where did Liam work in July 2023?", "Anthropic", "Where did Liam work in May 2024?", "DeepMind"),
    ("Hannah", "Boston", "2020-09-01", "Austin", "2023-01-01", "2022-01-01", "Where was Hannah living in January 2022?", "Boston", "Where was Hannah living in June 2023?", "Austin"),
    ("Kevin", "Snowflake", "2021-08-01", "Figma", "2023-10-01", "2022-11-01", "Where was Kevin employed in November 2022?", "Snowflake", "Where was Kevin employed in December 2023?", "Figma"),
    ("Zoe", "Toronto", "2021-01-01", "Vancouver", "2024-03-01", "2023-05-01", "Where did Zoe reside in May 2023?", "Toronto", "Where did Zoe reside in April 2024?", "Vancouver"),
    ("Ethan", "Microsoft", "2020-06-01", "Apple", "2023-08-01", "2022-09-01", "Where did Ethan work in September 2022?", "Microsoft", "Where did Ethan work in September 2023?", "Apple"),
]

for idx, (person, p_org, p_date, n_org, n_date, q_past_date, q_past, t_past, q_new, t_new) in enumerate(historical_scenarios, start=1):
    # Two queries per scenario = 20 queries total (hist_01 to hist_20)
    c_past_id = f"hist_{2*idx-1:02d}"
    c_new_id = f"hist_{2*idx:02d}"

    # Common seeds: historical state and updated state
    seeds = [
        {
            "content": f"{person} works at {p_org} as of {p_date}",
            "valid_from": f"{p_date}T00:00:00Z",
            "confidence": 1.0,
        },
        {
            "content": f"{person} left {p_org} and joined {n_org} in {n_date}",
            "valid_from": f"{n_date}T00:00:00Z",
            "confidence": 1.0,
        }
    ]

    cases.append({
        "id": c_past_id,
        "category": "historical_temporal",
        "query": q_past,
        "expected_target": t_past,
        "invalid_outdated_target": t_new,
        "valid_at": f"{q_past_date}T00:00:00Z",
        "facts_to_seed": seeds,
    })

    cases.append({
        "id": c_new_id,
        "category": "historical_temporal",
        "query": q_new,
        "expected_target": t_new,
        "invalid_outdated_target": t_past,
        "valid_at": f"{n_date}T12:00:00Z",
        "facts_to_seed": [],  # already seeded by partner case
    })

# ==============================================================================
# Category 3: Fact Updates & Contradictions (20 cases: contra_01 to contra_20)
# Testing confidence weighting, source reliability, and contradiction resolution
# ==============================================================================
contradiction_pairs = [
    (
        "contra_01",
        "What is the status of Project Valkyrie?",
        "Series B",
        "cancelled",
        "Unverified rumor claims Project Valkyrie was cancelled by leadership in 2024-03-01",
        0.20,
        "Official board announcement verifies Project Valkyrie received Series B expansion funding in 2024-03-01",
        0.99
    ),
    (
        "contra_02",
        "Where is the headquarters of NovaTech located?",
        "Stockholm",
        "Oslo",
        "Blog post speculates NovaTech relocated to Oslo in 2024-01-01",
        0.30,
        "Corporate registry legally confirms NovaTech headquarters is located in Stockholm in 2024-01-01",
        0.98
    ),
    (
        "contra_03",
        "What is the maximum certified cluster node capacity?",
        "1024 nodes",
        "128 nodes",
        "Preliminary draft notes maximum cluster size is 128 nodes in 2024-02-01",
        0.35,
        "Verified benchmark certification establishes maximum cluster size is 1024 nodes in 2024-02-01",
        0.99
    ),
    (
        "contra_04",
        "Who is the lead architect of the Quantum Engine?",
        "Dr. Aris",
        "Dr. Vance",
        "Unconfirmed forum post mentions Dr. Vance leads the Quantum Engine in 2024-04-01",
        0.25,
        "Engineering organization charter confirms Dr. Aris is the lead architect of Quantum Engine in 2024-04-01",
        0.97
    ),
    (
        "contra_05",
        "What encryption standard protects user tokens?",
        "AES-256-GCM",
        "DES",
        "Outdated tutorial claims user tokens use DES encryption in 2024-01-01",
        0.15,
        "Security audit report certifies user tokens are protected with AES-256-GCM in 2024-01-01",
        0.99
    ),
    (
        "contra_06",
        "What is the SLA availability commitment for Enterprise tier?",
        "99.99%",
        "95.0%",
        "Customer support ticket erroneously mentions 95.0% SLA in 2024-02-01",
        0.25,
        "Master service agreement legally guarantees 99.99% availability SLA in 2024-02-01",
        0.99
    ),
    (
        "contra_07",
        "Who was elected Chairman of the Technical Advisory Board?",
        "Professor Thorne",
        "Dr. Bailey",
        "Social media speculation named Dr. Bailey Chairman in 2024-03-01",
        0.30,
        "Formal press release announces Professor Thorne was elected Chairman in 2024-03-01",
        0.98
    ),
    (
        "contra_08",
        "What primary programming language powers the high-speed gateway?",
        "Rust",
        "PHP",
        "Informal chat comment guessed gateway is written in PHP in 2024-01-01",
        0.10,
        "Engineering repository manifest confirms gateway core is implemented in Rust in 2024-01-01",
        0.99
    ),
    (
        "contra_09",
        "What is the designated disaster recovery RPO target?",
        "5 minutes",
        "24 hours",
        "Outdated wiki page states disaster recovery RPO is 24 hours in 2024-01-01",
        0.20,
        "Disaster recovery policy dictates verified RPO threshold is 5 minutes in 2024-01-01",
        0.98
    ),
    (
        "contra_10",
        "Which cloud provider hosts the primary European production workloads?",
        "AWS Frankfurt",
        "DigitalOcean",
        "Discussion thread assumed European workloads run on DigitalOcean in 2024-02-01",
        0.20,
        "Infrastructure billing ledger confirms European workloads reside in AWS Frankfurt in 2024-02-01",
        0.99
    ),
    (
        "contra_11",
        "What is the memory limit allocated per serverless function instance?",
        "2048 MB",
        "256 MB",
        "Old staging documentation listed 256 MB per function in 2024-01-01",
        0.30,
        "Production deployment configuration allocates 2048 MB per serverless instance in 2024-01-01",
        0.99
    ),
    (
        "contra_12",
        "Who authored the foundational whitepaper on Chronos Protocol?",
        "Dr. Elizabeth Vance",
        "Anonymous",
        "Gossip bulletin credited an Anonymous collective for Chronos in 2024-02-01",
        0.15,
        "IEEE publication explicitly records Dr. Elizabeth Vance authored Chronos Protocol in 2024-02-01",
        0.99
    ),
    (
        "contra_13",
        "What is the official retention duration for compliance audit logs?",
        "7 years",
        "30 days",
        "Support note mistakenly suggested 30 days retention for audit logs in 2024-01-01",
        0.20,
        "Compliance regulatory mandate requires audit logs retention for 7 years in 2024-01-01",
        0.99
    ),
    (
        "contra_14",
        "What protocol is utilized for inter-cluster data replication?",
        "gRPC stream",
        "FTP",
        "Draft memo casually suggested using FTP for inter-cluster transfer in 2024-01-01",
        0.10,
        "Architecture review board approved gRPC stream for inter-cluster replication in 2024-01-01",
        0.98
    ),
    (
        "contra_15",
        "Who serves as the designated Data Protection Officer?",
        "Claire Moreau",
        "John Doe",
        "Placeholder mockup listed John Doe as Data Protection Officer in 2024-01-01",
        0.10,
        "Official legal filing appoints Claire Moreau as corporate Data Protection Officer in 2024-01-01",
        0.99
    ),
    (
        "contra_16",
        "What is the benchmark throughput achieved by the parsing engine?",
        "250,000 events/sec",
        "1,000 events/sec",
        "Staging prototype achieved 1,000 events/sec in 2024-01-01",
        0.30,
        "Validated production stress test certifies throughput of 250,000 events/sec in 2024-01-01",
        0.98
    ),
    (
        "contra_17",
        "What authentication standard is enforced for external developers?",
        "OAuth2 with PKCE",
        "HTTP Basic",
        "Legacy API sample used HTTP Basic auth in 2024-01-01",
        0.20,
        "API security guidelines enforce OAuth2 with PKCE for all developer integrations in 2024-01-01",
        0.99
    ),
    (
        "contra_18",
        "Which organization awarded the 2024 AI Infrastructure Excellence prize?",
        "ACM SIGOPS",
        "Local Gazette",
        "Casual newsletter claimed Local Gazette awarded the prize in 2024-04-01",
        0.25,
        "Official ceremony announcement confirms ACM SIGOPS awarded the 2024 Excellence prize in 2024-04-01",
        0.99
    ),
    (
        "contra_19",
        "What is the default isolation level in the relational transaction manager?",
        "Serializable",
        "Read Uncommitted",
        "Debugging note suggested Read Uncommitted for performance in 2024-02-01",
        0.20,
        "Database core specification enforces Serializable transaction isolation in 2024-02-01",
        0.99
    ),
    (
        "contra_20",
        "Who is the principal maintainer of the open-source client SDK?",
        "Yuki Tanaka",
        "External Vendor",
        "Third-party post claimed an External Vendor maintains the SDK in 2024-03-01",
        0.25,
        "GitHub repository governance formally designates Yuki Tanaka as principal SDK maintainer in 2024-03-01",
        0.99
    ),
]

for cid, query, valid_target, invalid_target, fake_txt, fake_conf, true_txt, true_conf in contradiction_pairs:
    cases.append({
        "id": cid,
        "category": "fact_updates_contradictions",
        "query": query,
        "expected_target": valid_target,
        "invalid_outdated_target": invalid_target,
        "valid_at": "2024-04-01T00:00:00Z",
        "facts_to_seed": [
            {
                "content": fake_txt,
                "valid_from": "2024-01-01T00:00:00Z",
                "confidence": fake_conf,
            },
            {
                "content": true_txt,
                "valid_from": "2024-01-01T00:00:00Z",
                "confidence": true_conf,
            }
        ]
    })

# ==============================================================================
# Category 4: Multi-Hop Relationship Retrieval (20 cases: multi_01 to multi_20)
# Testing recursive graph traversal across chained entities (A -> B -> C)
# ==============================================================================
multihop_scenarios = [
    # id, query, target, entA, rel1, entB, rel2, entC
    ("multi_01", "What project is managed by the leader of Team Phoenix?", "Project Aegis", "Marcus leads Team Phoenix", "Team Phoenix created Project Aegis"),
    ("multi_02", "In what city is the parent company of Lumina Studio located?", "Zurich", "Lumina Studio works at MediaGiant Corp", "MediaGiant Corp located in Zurich"),
    ("multi_03", "Which tool is maintained by the author of the Vector Paper?", "FastEmbed", "Dr. Chen created Vector Paper", "Vector Paper uses FastEmbed"),
    ("multi_04", "What operating system runs on the cluster founded by Alan?", "Alpine Linux", "Alan built Cluster Omega", "Cluster Omega adopted Alpine Linux"),
    ("multi_05", "Who is the advisor of the student who joined DeepMind?", "Professor Wu", "Alice works at DeepMind", "Professor Wu collaborates with Alice"),
    ("multi_06", "What database powers the platform owned by Helios Labs?", "PostgreSQL", "Helios Labs created Aurora Platform", "Aurora Platform uses PostgreSQL"),
    ("multi_07", "Which framework is used by the system designed by Brenda?", "PyTorch", "Brenda built VisionNet", "VisionNet adopted PyTorch"),
    ("multi_08", "What city hosts the subsidiary founded by Liam?", "Kyoto", "Liam founded Studio Kaze", "Studio Kaze located in Kyoto"),
    ("multi_09", "Who manages the division that created the Chronos Engine?", "Director Vance", "Director Vance works at Division Nine", "Division Nine created Chronos Engine"),
    ("multi_10", "What language is used in the benchmark tool created by Samuel?", "Rust", "Samuel built BenchCore", "BenchCore adopted Rust"),
    ("multi_11", "Where is the research facility created by Dr. Aris located?", "Geneva", "Dr. Aris founded CERN Lab", "CERN Lab located in Geneva"),
    ("multi_12", "What caching technology is adopted by the gateway owned by Apex?", "Redis", "Apex owns Gateway Pro", "Gateway Pro uses Redis"),
    ("multi_13", "Who is the mentor of the engineer who created TensorMesh?", "Dr. Thorne", "Kai created TensorMesh", "Dr. Thorne collaborates with Kai"),
    ("multi_14", "What standard is enforced by the consortium joined by NovaTech?", "ISO-27001", "NovaTech joined Security Alliance", "Security Alliance adopted ISO-27001"),
    ("multi_15", "Which cloud region hosts the storage service built by Elena?", "us-east-1", "Elena built ObjectStore", "ObjectStore located in us-east-1"),
    ("multi_16", "What message broker is integrated into the event bus created by Clara?", "Apache Kafka", "Clara created EventPipeline", "EventPipeline uses Apache Kafka"),
    ("multi_17", "In what headquarters city does the founder of Project Titan work?", "Tokyo", "Kenji created Project Titan", "Kenji located in Tokyo"),
    ("multi_18", "Which neural network architecture is leveraged by the bot designed by Omar?", "Transformer", "Omar built SynthBot", "SynthBot uses Transformer"),
    ("multi_19", "Who is the partner of the executive who leads Falcon Ventures?", "Diana Prince", "Bruce Wayne works at Falcon Ventures", "Bruce Wayne collaborates with Diana Prince"),
    ("multi_20", "What serialization format is utilized by the telemetry daemon built by Isaac?", "FlatBuffers", "Isaac built Telemetry Daemon", "Telemetry Daemon adopted FlatBuffers"),
]

for cid, query, target, f1, f2 in multihop_scenarios:
    cases.append({
        "id": cid,
        "category": "multihop_graph",
        "query": query,
        "expected_target": target,
        "invalid_outdated_target": None,
        "valid_at": "2024-05-01T00:00:00Z",
        "facts_to_seed": [
            {
                "content": f"{f1} in 2024-01-01",
                "valid_from": "2024-01-01T00:00:00Z",
                "confidence": 1.0,
            },
            {
                "content": f"{f2} in 2024-02-01",
                "valid_from": "2024-02-01T00:00:00Z",
                "confidence": 1.0,
            }
        ]
    })

# ==============================================================================
# Category 5: Outdated vs Current Information (20 cases: curr_01 to curr_20)
# Testing queries asking for CURRENT state when superseded historical facts exist
# ==============================================================================
current_vs_outdated = [
    # id, query, current_target, outdated_target, old_fact, new_fact
    (
        "curr_01",
        "What is the current primary database host?",
        "aurora-cluster-main",
        "db-primary-01",
        "Primary database host is db-primary-01 as of 2022-01-01",
        "Primary database host was migrated to aurora-cluster-main in 2024-01-01"
    ),
    (
        "curr_02",
        "What port does the production API gateway listen on?",
        "443",
        "8080",
        "Production API gateway listens on port 8080 as of 2021-06-01",
        "Production API gateway listens on port 443 with TLS termination in 2023-12-01"
    ),
    (
        "curr_03",
        "Who is the current Head of Engineering at Apex Systems?",
        "Victoria Zhao",
        "Robert Miller",
        "Robert Miller is the Head of Engineering at Apex Systems in 2021-01-01",
        "Victoria Zhao joined Apex Systems as Head of Engineering in 2024-01-15"
    ),
    (
        "curr_04",
        "What is the active default branch for the core repository?",
        "main",
        "master",
        "The default repository branch was master in 2020-01-01",
        "The default repository branch is main in 2023-01-01"
    ),
    (
        "curr_05",
        "What is the current rate limit per minute on public API keys?",
        "1000 requests",
        "60 requests",
        "Public API rate limit was set to 60 requests in 2021-01-01",
        "Public API rate limit was upgraded to 1000 requests in 2024-02-01"
    ),
    (
        "curr_06",
        "What Python version is mandated in production runtime environments?",
        "Python 3.11",
        "Python 3.8",
        "Production runtime requires Python 3.8 as of 2020-05-01",
        "Production runtime mandates Python 3.11 in 2024-01-01"
    ),
    (
        "curr_07",
        "Where is the corporate finance office currently located?",
        "New York",
        "Chicago",
        "Corporate finance office was located in Chicago in 2021-03-01",
        "Corporate finance office relocated to New York in 2023-11-01"
    ),
    (
        "curr_08",
        "What is the active consensus protocol used by the ledger?",
        "BFT-Raft",
        "Proof of Work",
        "Ledger protocol used Proof of Work in 2020-01-01",
        "Ledger protocol transitioned to BFT-Raft in 2023-10-01"
    ),
    (
        "curr_09",
        "Who is the current on-call lead for the Storage Squad?",
        "Darius Stone",
        "Emma Watson",
        "Emma Watson was on-call lead for the Storage Squad in 2022-01-01",
        "Darius Stone is on-call lead for the Storage Squad in 2024-03-01"
    ),
    (
        "curr_10",
        "What container registry is currently used for deployment images?",
        "GitHub Packages",
        "DockerHub",
        "Deployment images were hosted on DockerHub in 2021-04-01",
        "Deployment images are hosted on GitHub Packages in 2023-08-01"
    ),
    (
        "curr_11",
        "What is the current maximum payload size for webhook ingestion?",
        "10 MB",
        "1 MB",
        "Webhook ingestion payload limit was 1 MB in 2021-01-01",
        "Webhook ingestion payload limit was raised to 10 MB in 2024-01-01"
    ),
    (
        "curr_12",
        "Who is the active Chief Security Officer?",
        "Miranda Bell",
        "Gregory House",
        "Gregory House served as Chief Security Officer in 2020-01-01",
        "Miranda Bell was appointed Chief Security Officer in 2023-09-01"
    ),
    (
        "curr_13",
        "What vector indexing algorithm is currently active in production?",
        "HNSW",
        "IVFFlat",
        "Vector search index used IVFFlat in 2022-01-01",
        "Vector search index was replaced by HNSW in 2024-01-01"
    ),
    (
        "curr_14",
        "What TLS version is mandated for all ingress connections?",
        "TLS 1.3",
        "TLS 1.1",
        "Ingress connections allowed TLS 1.1 in 2019-01-01",
        "Ingress connections strictly require TLS 1.3 in 2023-07-01"
    ),
    (
        "curr_15",
        "Where does the central documentation site currently live?",
        "docs.mnemos.io",
        "wiki.internal",
        "Central documentation site was wiki.internal in 2020-01-01",
        "Central documentation site migrated to docs.mnemos.io in 2024-01-01"
    ),
    (
        "curr_16",
        "What is the current memory allocation per API pod?",
        "4 GB",
        "512 MB",
        "API pod memory allocation was 512 MB in 2021-01-01",
        "API pod memory allocation is 4 GB in 2024-02-01"
    ),
    (
        "curr_17",
        "Who is currently directing the AI Research Initiative?",
        "Dr. Lucas Frost",
        "Dr. Simon Gray",
        "Dr. Simon Gray was directing AI Research in 2021-05-01",
        "Dr. Lucas Frost is directing AI Research in 2024-01-01"
    ),
    (
        "curr_18",
        "What authentication protocol protects internal admin dashboards?",
        "Okta SAML SSO",
        "Basic Auth",
        "Internal admin dashboard used Basic Auth in 2020-01-01",
        "Internal admin dashboard enforces Okta SAML SSO in 2023-11-01"
    ),
    (
        "curr_19",
        "What is the current log retention window in Elasticsearch?",
        "90 days",
        "7 days",
        "Elasticsearch log retention was 7 days in 2021-01-01",
        "Elasticsearch log retention was extended to 90 days in 2024-01-01"
    ),
    (
        "curr_20",
        "Who is the active product manager for the Developer Console?",
        "Nadia Perez",
        "Tom Clark",
        "Tom Clark was product manager for Developer Console in 2022-01-01",
        "Nadia Perez is product manager for Developer Console in 2024-02-01"
    ),
]

for cid, query, curr_target, old_target, old_txt, new_txt in current_vs_outdated:
    cases.append({
        "id": cid,
        "category": "outdated_vs_current",
        "query": query,
        "expected_target": curr_target,
        "invalid_outdated_target": old_target,
        "valid_at": "2024-05-01T00:00:00Z",
        "facts_to_seed": [
            {
                "content": old_txt,
                "valid_from": "2021-01-01T00:00:00Z",
                "confidence": 1.0,
            },
            {
                "content": new_txt,
                "valid_from": "2024-01-01T00:00:00Z",
                "confidence": 1.0,
            }
        ]
    })

dataset_path = "benchmarks/datasets/temporal_qa.json"
os.makedirs(os.path.dirname(dataset_path), exist_ok=True)
with open(dataset_path, "w", encoding="utf-8") as f:
    json.dump(cases, f, indent=2)

print(f"Generated {len(cases)} benchmark test cases across 5 categories in '{dataset_path}'")
by_cat = {}
for c in cases:
    by_cat[c["category"]] = by_cat.get(c["category"], 0) + 1
for cat, count in by_cat.items():
    print(f"  - {cat}: {count} queries")

# Nexa Architecture V2

```text
                     +----------------------+
                     |   Web / Mobile UI    |
                     +----------+-----------+
                                |
                                v
                     +----------------------+
                     |   FastAPI API Layer  |
                     | auth | courses | AI  |
                     | live | learning      |
                     +----+----------+------+
                          |          |
             +------------+          +----------------+
             v                                         v
      +-------------+                           +-------------+
      | PostgreSQL  |                           |    Redis    |
      | system data |                           | cache/jobs  |
      +-------------+                           +-------------+
             |
             +------------------+
                                v
                    +-----------------------+
                    | Learning Intelligence |
                    | skills / paths / recs |
                    +-----------+-----------+
                                |
                  +-------------+-------------+
                  v                           v
           +-------------+             +-------------+
           | Vector DB   |             | LLM Provider |
           | course RAG  |             | Tutor / AI   |
           +-------------+             +-------------+

 Live media:
 Browser <---- WebRTC / SFU ----> Browser
                ^
                |
          FastAPI signaling
```

The current repository keeps a modular monolith so the product can evolve quickly. Services should only be split after real scaling or ownership boundaries justify it.

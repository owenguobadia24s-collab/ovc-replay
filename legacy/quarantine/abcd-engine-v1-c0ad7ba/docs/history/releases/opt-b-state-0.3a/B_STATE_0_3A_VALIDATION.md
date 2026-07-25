# B-STATE-0.3a Validation

**Status:** `PASS`  
**Validated manifest:** `c52613fea5ef27c7331896b4afcc08ddf6c74048bdcf9a8f2a7d78c0b5f686cd`  
**Manifest-bound artifacts:** `11`  
**Independent replay determinism:** `PASS`

Every gzip stream decompressed fully, every declared artifact hash matched, state rows were unique by close time, record counts matched the manifest, categorical acceptance did not leak into the relation inventory, frozen non-acceptance axes matched v0.3, and no outcome or execution fields entered the replay.

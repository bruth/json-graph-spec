# JSON Graph Spec

JSON specficiation for defining nodes and relationships for import/export. This is based on the capability of Neo4j's MERGE statement (create or update), however it is not specific to the implementation.

### Example

```javascript
{
    "nodes": [{
        "labels": ["Origin"],
        "props": {
            "name": "file.csv",
            "uri": "csv:///path/to/file.csv"
        },
        "match": ["uri"]
    }, {
        "labels": ["Element"],
        "props": {
            "name": "ArtistId",
            "uri": "csv:///path/to/file.csv/ArtistId"
        },
        "match": ["uri"]
    }],
    "rels": [{
        "start": 0,
        "end": 1,
        "type": "CONTAINS"
    }]
}
```

### Structure

- `nodes` - An array of objects representing nodes
- `rels` - An array of objects representing relationships

### General Options
- `props` - Object of properties to be set on the node. By default all properties defined here will be used to match on and then be merged into existing properties on the node. See the additional options below to customize this behavior.
- `match` - Array of property keys or an object to match on. If not defined, all properties much match. If `false` the node will be forced created (note, that any constraints in the database may cause the create the fail)
- `update` - Array of property keys or an object to update if a match exists. If not defined, all properties are updated.
- `replace` - A boolean denoting if on an update the existing properties should be replaced vs. updating each individual property. By default, this is `false`.

### Node Specific Options
- `labels` - Set the labels on the node. On an update, this will replace any existing labels.

### Relationship Specific Options
- `start` - The integer index in the `nodes` array of the start node
- `end` - The integer index in the `nodes` array of the end node
- `type` - The relationship type

## Implementations

### Python

```
./neo4j.py [-p] /path/to/file.json [http://localhost:7474/db/data/]
```

If `-p` is passed, the statements will be printed to stdout rather than be loaded into Neo4j. An alternate endpoint can be supplied as the second argument if not using the default.

# JSON Graph Spec

JSON specficiation for defining nodes and relationships for import/export. This is based on the capability of Neo4j's MERGE statement (create or update), however it is not specific to the implementation.

## Object-based Format

An object with the following keys:

- `nodes` - An array of objects representing nodes
- `rels` - An array of objects representing relationships

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

## Array-based Format

An array of objects with nodes and relationships interleaved.

```javascript
[{
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
}, {
    "start": 0,
    "end": 1,
    "type": "CONTAINS"
}]

### General Options

- `props` - Object of properties to be set on the node. By default all properties defined here will be used to match on and then be merged into existing properties on the node. See the additional options below to customize this behavior.
- `match` - Array of property keys or an object to match on. If not defined, all properties much match. If `false` the node will be forced created (note, that any constraints in the database may cause the create the fail). If `true`, `MERGE` will be foced without any properties specified.
- `update` - Array of property keys or an object to update if a match exists. If not defined, all properties are updated.
- `replace` - A boolean denoting if on an update the existing properties should be replaced vs. updating each individual property. By default, this is `false`.

### Node Specific Options

- `labels` - Set of labels on the node. On an update, this will replace any existing labels.

### Relationship Specific Options

- `start` (required) - The integer index of the start node in the array the node is defined.
- `end` (required) - The integer index of the end node in the array the node is defined.
- `type` (required) - The relationship type

*If `match` is not defined, it defaults to `true` for relationships since it is less common to create multiple relationships of the same type between the same two nodes.*

## Implementations

- [graphlib](https://github.com/bruth/graphlib/) - Python

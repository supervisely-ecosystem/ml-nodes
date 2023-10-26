# Images Project

`Images Project` layer is used to specify project and its datasets that will participate in data transformation process. It allows to select classes that will be used in data transformation process.

### Settings:

- **Select Project** - Select project and specify datasets that will participate in data transformation process.
- **Classes** - Select classes that will be used in data transformation processes from selected Project if it have any.

### Example 1. Select all datasets and classes

In this example we will select all datasets and classes.

It means that **all data will be used in data transformation processes**.

### Example 2. Select specific datasets and classes

In this example we will select specific `animal` dataset and `raccoon` class.

It will keep **all images from `animal` dataset** but **only `raccoon` class objects** will be used in data transformation processes.

![data-2](https://github.com/supervisely-ecosystem/ml-nodes/assets/79905215/4c6c66db-3197-4c76-add6-c1107cb0ecc5)

### JSON views

<details>
  <summary>All datasets and classes</summary>
<pre>
{
  "action": "data",
  "src": ["My project/*"],
  "dst": "$data_15",
  "settings": {
    "classes_mapping": {
      "blueberries": "blueberries",
      "dog": "dog",
      "tree": "tree",
      "raccoon": "raccoon",
      "plants": "plants"
    }
  }
}
</pre>
</details>

<details>
  <summary>Specific datasets and classes</summary>
<pre>
{
  "action": "data",
  "src": ["My project/animals"],
  "dst": "$data_15",
  "settings": {
    "classes_mapping": {
      "blueberries": "__ignore__",
      "raccoon": "raccoon",
      "dog": "__ignore__",
      "plants": "__ignore__",
      "tree": "__ignore__"
    }
  }
}
</pre>
</details>
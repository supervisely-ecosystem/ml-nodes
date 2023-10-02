# Rasterize

Layer for rasterizing objects on image (i.e. one pixel will belong to only one object)

### Settings

- **Select classes** (class selection mode)

```json
{
    "action": "rasterize",
    "src": [
        "$data_12"
    ],
    "dst": "$rasterize_17",
    "settings": {
        "classes_mapping": {
            "Car": "Car_Rasterized",
            "Road": "Road_Rasterized"
        }
    }
}
```

### Example

<table>
<tr>
<td style="text-align:center"><strong>Original image</strong></td>
<td style="text-align:center"><strong>Only Road label</strong></td>
<td style="text-align:center"><strong>Road with rasterized Car object</strong></td>
</tr>
<tr>
<td> <img src="https://github.com/supervisely-ecosystem/dtl-v2/assets/79905215/c0533a4e-a1b7-44e7-814c-aaa15c40eec8" alt="Original image" /> </td>
<td> <img src="https://github.com/supervisely-ecosystem/dtl-v2/assets/79905215/d589d6f1-1510-412a-be29-d876eda09f4d" alt="Only Road label" /> </td>
<td> <img src="https://github.com/supervisely-ecosystem/dtl-v2/assets/79905215/fd45dad9-9653-40dc-bc5e-619d18709a61" alt="Road with rasterized Car object" /> </td>
</tr>
</table>
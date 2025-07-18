interface SortableObject {
  [key: string]: any;
}

export function sortObjectByOrder(obj: SortableObject): SortableObject {
  if (obj.Order && Array.isArray(obj.Order)) {
    const orderedObj: SortableObject = {};

    obj.Order.forEach((key: string) => {
      if (obj[key]) {
        orderedObj[key] = obj[key];
      }
    });

    Object.keys(orderedObj).forEach((key) => {
      if (orderedObj[key] && typeof orderedObj[key] === "object") {
        orderedObj[key] = sortObjectByOrder(orderedObj[key]);
      }
    });

    return orderedObj;
  }

  for (const key in obj) {
    if (obj[key] && typeof obj[key] === "object") {
      obj[key] = sortObjectByOrder(obj[key]);
    }
  }

  return obj;
}

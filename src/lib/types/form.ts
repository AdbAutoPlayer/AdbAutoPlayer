interface FormDataGeneric {
  [section: string]: {
    [key: string]: string | number | boolean | Array<string | number | boolean>;
  };
}

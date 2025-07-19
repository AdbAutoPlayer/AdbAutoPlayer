export namespace config {
  export class ADBConfig {
    Host: string;
    Port: number;

    static createFrom(source: any = {}) {
      return new ADBConfig(source);
    }

    constructor(source: any = {}) {
      if ("string" === typeof source) source = JSON.parse(source);
      this.Host = source["Host"];
      this.Port = source["Port"];
    }
  }
  export class DeviceConfig {
    ID: string;
    "Resize Display (Phone/Tablet only)": boolean;
    "Device Streaming (disable for slow PCs)": boolean;
    "Enable Hardware Decoding": boolean;

    static createFrom(source: any = {}) {
      return new DeviceConfig(source);
    }

    constructor(source: any = {}) {
      if ("string" === typeof source) source = JSON.parse(source);
      this.ID = source["ID"];
      this["Resize Display (Phone/Tablet only)"] =
        source["Resize Display (Phone/Tablet only)"];
      this["Device Streaming (disable for slow PCs)"] =
        source["Device Streaming (disable for slow PCs)"];
      this["Enable Hardware Decoding"] = source["Enable Hardware Decoding"];
    }
  }
  export class LoggingConfig {
    "Log Level": string;
    "Debug Screenshot Limit": number;
    "Action Log Limit": number;

    static createFrom(source: any = {}) {
      return new LoggingConfig(source);
    }

    constructor(source: any = {}) {
      if ("string" === typeof source) source = JSON.parse(source);
      this["Log Level"] = source["Log Level"];
      this["Debug Screenshot Limit"] = source["Debug Screenshot Limit"];
      this["Action Log Limit"] = source["Action Log Limit"];
    }
  }
  export class UIConfig {
    Theme: string;
    Language: string;

    static createFrom(source: any = {}) {
      return new UIConfig(source);
    }

    constructor(source: any = {}) {
      if ("string" === typeof source) source = JSON.parse(source);
      this.Theme = source["Theme"];
      this.Language = source["Language"];
    }
  }
  export class UpdateConfig {
    "Automatically download updates": boolean;
    "Download Alpha updates": boolean;

    static createFrom(source: any = {}) {
      return new UpdateConfig(source);
    }

    constructor(source: any = {}) {
      if ("string" === typeof source) source = JSON.parse(source);
      this["Automatically download updates"] =
        source["Automatically download updates"];
      this["Download Alpha updates"] = source["Download Alpha updates"];
    }
  }
  export class MainConfig {
    "ADB (Advanced)": ADBConfig;
    Device: DeviceConfig;
    Update: UpdateConfig;
    Logging: LoggingConfig;
    "User Interface": UIConfig;

    static createFrom(source: any = {}) {
      return new MainConfig(source);
    }

    constructor(source: any = {}) {
      if ("string" === typeof source) source = JSON.parse(source);
      this["ADB (Advanced)"] = this.convertValues(
        source["ADB (Advanced)"],
        ADBConfig,
      );
      this.Device = this.convertValues(source["Device"], DeviceConfig);
      this.Update = this.convertValues(source["Update"], UpdateConfig);
      this.Logging = this.convertValues(source["Logging"], LoggingConfig);
      this["User Interface"] = this.convertValues(
        source["User Interface"],
        UIConfig,
      );
    }

    convertValues(a: any, classs: any, asMap: boolean = false): any {
      if (!a) {
        return a;
      }
      if (a.slice && a.map) {
        return (a as any[]).map((elem) => this.convertValues(elem, classs));
      } else if ("object" === typeof a) {
        if (asMap) {
          for (const key of Object.keys(a)) {
            a[key] = new classs(a[key]);
          }
          return a;
        }
        return new classs(a);
      }
      return a;
    }
  }
}

export namespace ipc {
  export class MenuOption {
    label: string;
    translated?: boolean;
    args: string[];
    category?: string;
    tooltip?: string;

    static createFrom(source: any = {}) {
      return new MenuOption(source);
    }

    constructor(source: any = {}) {
      if ("string" === typeof source) source = JSON.parse(source);
      this.label = source["label"];
      this.translated = source["translated"];
      this.args = source["args"];
      this.category = source["category"];
      this.tooltip = source["tooltip"];
    }
  }
  export class GameGUI {
    game_title: string;
    config_path: string;
    menu_options: MenuOption[];
    categories?: string[];
    constraints: Record<string, any>;

    static createFrom(source: any = {}) {
      return new GameGUI(source);
    }

    constructor(source: any = {}) {
      if ("string" === typeof source) source = JSON.parse(source);
      this.game_title = source["game_title"];
      this.config_path = source["config_path"];
      this.menu_options = this.convertValues(
        source["menu_options"],
        MenuOption,
      );
      this.categories = source["categories"];
      this.constraints = source["constraints"];
    }

    convertValues(a: any, classs: any, asMap: boolean = false): any {
      if (!a) {
        return a;
      }
      if (a.slice && a.map) {
        return (a as any[]).map((elem) => this.convertValues(elem, classs));
      } else if ("object" === typeof a) {
        if (asMap) {
          for (const key of Object.keys(a)) {
            a[key] = new classs(a[key]);
          }
          return a;
        }
        return new classs(a);
      }
      return a;
    }
  }
}

export namespace updater {
  export class Changelog {
    body: string;
    version: string;

    static createFrom(source: any = {}) {
      return new Changelog(source);
    }

    constructor(source: any = {}) {
      if ("string" === typeof source) source = JSON.parse(source);
      this.body = source["body"];
      this.version = source["version"];
    }
  }
  export class UpdateInfo {
    available: boolean;
    version: string;
    downloadURL: string;
    size: number;
    autoUpdate: boolean;

    static createFrom(source: any = {}) {
      return new UpdateInfo(source);
    }

    constructor(source: any = {}) {
      if ("string" === typeof source) source = JSON.parse(source);
      this.available = source["available"];
      this.version = source["version"];
      this.downloadURL = source["downloadURL"];
      this.size = source["size"];
      this.autoUpdate = source["autoUpdate"];
    }
  }
}

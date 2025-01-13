export namespace afkjourney {
	
	export class AFKStagesConfig {
	    Attempts: number;
	    Formations: number;
	    "Use suggested Formations": boolean;
	    "Push both modes": boolean;
	    "Spend Gold": boolean;
	
	    static createFrom(source: any = {}) {
	        return new AFKStagesConfig(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.Attempts = source["Attempts"];
	        this.Formations = source["Formations"];
	        this["Use suggested Formations"] = source["Use suggested Formations"];
	        this["Push both modes"] = source["Push both modes"];
	        this["Spend Gold"] = source["Spend Gold"];
	    }
	}
	export class DurasTrialsConfig {
	    Attempts: number;
	    Formations: number;
	    "Use suggested Formations": boolean;
	    "Spend Gold": boolean;
	
	    static createFrom(source: any = {}) {
	        return new DurasTrialsConfig(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.Attempts = source["Attempts"];
	        this.Formations = source["Formations"];
	        this["Use suggested Formations"] = source["Use suggested Formations"];
	        this["Spend Gold"] = source["Spend Gold"];
	    }
	}
	export class GeneralConfig {
	    "Excluded Heroes": string[];
	    "Assist Limit": number;
	
	    static createFrom(source: any = {}) {
	        return new GeneralConfig(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this["Excluded Heroes"] = source["Excluded Heroes"];
	        this["Assist Limit"] = source["Assist Limit"];
	    }
	}
	export class Config {
	    General: GeneralConfig;
	    "AFK Stages": AFKStagesConfig;
	    "Duras Trials": DurasTrialsConfig;
	
	    static createFrom(source: any = {}) {
	        return new Config(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.General = this.convertValues(source["General"], GeneralConfig);
	        this["AFK Stages"] = this.convertValues(source["AFK Stages"], AFKStagesConfig);
	        this["Duras Trials"] = this.convertValues(source["Duras Trials"], DurasTrialsConfig);
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
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

export namespace config {
	
	export class ADBConfig {
	    Host: string;
	    Port: number;
	
	    static createFrom(source: any = {}) {
	        return new ADBConfig(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.Host = source["Host"];
	        this.Port = source["Port"];
	    }
	}
	export class DeviceConfig {
	    ID: string;
	
	    static createFrom(source: any = {}) {
	        return new DeviceConfig(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.ID = source["ID"];
	    }
	}
	export class LoggingConfig {
	    Level: string;
	
	    static createFrom(source: any = {}) {
	        return new LoggingConfig(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.Level = source["Level"];
	    }
	}
	export class MainConfig {
	    Device: DeviceConfig;
	    ADB: ADBConfig;
	    Logging: LoggingConfig;
	
	    static createFrom(source: any = {}) {
	        return new MainConfig(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.Device = this.convertValues(source["Device"], DeviceConfig);
	        this.ADB = this.convertValues(source["ADB"], ADBConfig);
	        this.Logging = this.convertValues(source["Logging"], LoggingConfig);
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
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

export namespace games {
	
	export class MenuOption {
	    Label: string;
	    Args: string[];
	
	    static createFrom(source: any = {}) {
	        return new MenuOption(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.Label = source["Label"];
	        this.Args = source["Args"];
	    }
	}
	export class Game {
	    GameTitle: string;
	    ConfigPath: string;
	    ExePath: string;
	    PackageNames: string[];
	    MenuOptions: MenuOption[];
	    ConfigConstraints: {[key: string]: any};
	
	    static createFrom(source: any = {}) {
	        return new Game(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.GameTitle = source["GameTitle"];
	        this.ConfigPath = source["ConfigPath"];
	        this.ExePath = source["ExePath"];
	        this.PackageNames = source["PackageNames"];
	        this.MenuOptions = this.convertValues(source["MenuOptions"], MenuOption);
	        this.ConfigConstraints = source["ConfigConstraints"];
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
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


function to_param_url(paramsDict) {
    let url = '/users';
    let paramsList = [];
    for (const key in paramsDict) {
        if (paramsDict[key] !== null && paramsDict[key] !== undefined && paramsDict[key] !== "") {
            paramsList.push(`${'${encodeURIComponent(key)}'}=${'${encodeURIComponent(paramsDict[key])}'}`);
        }
    }
    if (paramsList.length > 0) { url += "?" + paramsList.join("&"); }
    window.location.href = url;
}
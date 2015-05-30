// determine if a variable is set and not to null (recursively based on arguments)
function isset() {
    var length = arguments.length;
    if(length == 0) return false;

    var object = arguments[0];
    if(object == null) return false;
    if(typeof object == 'undefined') return false;

    for(var i=1, n=length; i<n; ++i) {
        var key = arguments[i];
        if(typeof object[key] != 'undefined' && object[key] != null) {
            object = object[key];
        }
        else {
            return false;
        }
    }
    return true;
}
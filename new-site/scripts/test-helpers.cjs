// Other feature suites assume the visitor has already acknowledged the notice.
// Cookie persistence and the initial state are tested separately in test-cookies.cjs.
exports.acceptCookieNotice=target=>target.addInitScript(()=>{
 try{localStorage.setItem('molberty-cookie-consent','accepted-v1')}catch{}
});

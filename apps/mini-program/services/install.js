const env=require('../config/env');
module.exports=env.mode==='demo'?require('./demo'):require('./remote');

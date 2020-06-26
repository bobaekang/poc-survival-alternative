library(plumber)

app <- plumb("./plumber.R")
app$registerHook("postroute", function(req, res) {
  message(paste0(
    req$SERVER_NAME,
    " - - ",
    format(Sys.time(), "[%d/%b/%Y %H:%M:%S]"),
    ' "',
    req$REQUEST_METHOD,
    ' ',
    req$PATH_INFO,
    req$QUERY_STRING,
    '" ',
    res$status,
    " -"
  ))
})

app$run(port = 8080)

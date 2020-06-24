library(plumber)

app <- plumb("./plumber.R")
app$run(port = 8080)

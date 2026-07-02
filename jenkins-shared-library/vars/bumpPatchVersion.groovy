// Read MAJOR.MINOR.PATCH from the version file, increment PATCH, write it back,
// and return the new version string.
def call(String file = 'VERSION') {
  def parts = readFile(file).trim().tokenize('.')
  if (parts.size() != 3) { error("${file} is not MAJOR.MINOR.PATCH: ${parts}") }
  parts[2] = (parts[2].toInteger() + 1).toString()
  def next = parts.join('.')
  writeFile file: file, text: next + '\n'
  return next
}

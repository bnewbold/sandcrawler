package sandcrawler

import java.io.InputStream

import scala.io.Source

import org.scalatest._

// scalastyle:off null
class ScorableFeaturesTest extends FlatSpec with Matchers {

  private def titleToSlug(s : String) : String = {
    ScorableFeatures.create(title = s).toSlug
  }

  "toMapFeatures()" should "work with gnarly inputs" in {
    ScorableFeatures.create(title = null).toMapFeatures
    ScorableFeatures.create(title = "something", doi = null, sha1 = null, year = 123).toMapFeatures
  }

  "mapToSlug()" should "extract the parts of titles before a colon" in {
    titleToSlug("HELLO:there") shouldBe "hellothere"
  }

  it should "extract an entire colon-less string" in {
    titleToSlug("hello THERE") shouldBe "hellothere"
  }

  it should "return Scorable.NoSlug if given empty string" in {
    titleToSlug("") shouldBe Scorable.NoSlug
  }

  it should "return Scorable.NoSlug if given null" in {
    titleToSlug(null) shouldBe Scorable.NoSlug
  }

  it should "strip punctuation" in {
    titleToSlug("HELLO!:the:re") shouldBe "hellothere"
    titleToSlug("a:b:cdefgh") shouldBe "abcdefgh"
    titleToSlug(
      "If you're happy and you know it, clap your hands!") shouldBe "ifyourehappyandyouknowitclapyourhands"
    titleToSlug(":;\"\'") shouldBe Scorable.NoSlug
  }

  it should "filter stub titles" in {
    titleToSlug("abstract") shouldBe Scorable.NoSlug
    titleToSlug("title!") shouldBe Scorable.NoSlug
    titleToSlug("a real title which is not on blacklist") shouldBe "arealtitlewhichisnotonblacklist"
  }

  it should "strip special characters" in {
    titleToSlug(":;!',|\"\'`.#?!-@*/\\=+~%$^{}()[]<>-_’·“”‘’“”«»「」") shouldBe Scorable.NoSlug
    // TODO: titleToSlug("©™₨№…") shouldBe Scorable.NoSlug
    // TODO: titleToSlug("πµΣσ") shouldBe Scorable.NoSlug
  }

  it should "remove whitespace" in {
    titleToSlug("foo bar : baz ::") shouldBe "foobarbaz"
    titleToSlug("\na\t:b:cdefghi") shouldBe "abcdefghi"
    titleToSlug("\n \t \r  ") shouldBe Scorable.NoSlug
  }

  it should "skip very short slugs" in {
    titleToSlug("short") shouldBe Scorable.NoSlug
    titleToSlug("a longer, more in depth title") shouldBe "alongermoreindepthtitle"
  }
}

package sandcrawler

import cascading.tuple.Fields
import cascading.tuple.Tuple
import com.twitter.scalding.JobTest
import com.twitter.scalding.TextLine
import com.twitter.scalding.TupleConversions
import com.twitter.scalding.TypedTsv
import org.apache.hadoop.hbase.io.ImmutableBytesWritable
import org.apache.hadoop.hbase.util.Bytes
import org.scalatest._
import parallelai.spyglass.hbase.HBaseConstants.SourceMode

class CrossrefScorableTest extends FlatSpec with Matchers {
  // scalastyle:off
  val CrossrefString =
"""
{ "_id" : { "$oid" : "5a553d5988a035a45bf50ed3" },
  "indexed" : { "date-parts" : [ [ 2017, 10, 23 ] ],
    "date-time" : "2017-10-23T17:19:16Z",
    "timestamp" : { "$numberLong" : "1508779156477" } },
  "reference-count" : 0,
  "publisher" : "Elsevier BV",
  "issue" : "3",
  "license" : [ { "URL" : "http://www.elsevier.com/tdm/userlicense/1.0/",
                    "start" : { "date-parts" : [ [ 1996, 1, 1 ] ],
                                "date-time" : "1996-01-01T00:00:00Z",
                                "timestamp" : { "$numberLong" : "820454400000" } },
                                "delay-in-days" : 0, "content-version" : "tdm" }],
  "content-domain" : { "domain" : [], "crossmark-restriction" : false },
  "published-print" : { "date-parts" : [ [ 1996 ] ] },
  "DOI" : "<<DOI>>",
  "type" : "journal-article",
  "created" : { "date-parts" : [ [ 2002, 7, 25 ] ],
    "date-time" : "2002-07-25T15:09:41Z",
    "timestamp" : { "$numberLong" : "1027609781000" } },
  "page" : "186-187",
  "source" : "Crossref",
  "is-referenced-by-count" : 0,
  "title" : [ "<<TITLE>>" ],
  "prefix" : "10.1016",
  "volume" : "9",
  "author" : [ { "given" : "W", "family" : "Gaier", "affiliation" : [] } ],
  "member" : "78",
  "container-title" : [ "Journal de PÃ©diatrie et de PuÃ©riculture" ],
  "link" : [ { "URL" :  "http://api.elsevier.com/content/article/PII:0987-7983(96)87729-2?httpAccept=text/xml",
               "content-type" : "text/xml",
                 "content-version" : "vor",
                 "intended-application" : "text-mining" },
               { "URL" :
  "http://api.elsevier.com/content/article/PII:0987-7983(96)87729-2?httpAccept=text/plain",
                 "content-type" : "text/plain",
                 "content-version" : "vor",
                 "intended-application" : "text-mining" } ],
  "deposited" : { "date-parts" : [ [ 2015, 9, 3 ] ],
                  "date-time" : "2015-09-03T10:03:43Z",
                  "timestamp" : { "$numberLong" : "1441274623000" } },
  "score" : 1,
  "issued" : { "date-parts" : [ [ 1996 ] ] },
  "references-count" : 0,
  "alternative-id" : [ "0987-7983(96)87729-2" ],
  "URL" : "http://dx.doi.org/10.1016/0987-7983(96)87729-2",
  "ISSN" : [ "0987-7983" ],
  "issn-type" : [ { "value" : "0987-7983", "type" : "print" } ],
  "subject" : [ "Pediatrics, Perinatology, and Child Health" ]
}
""".replace("<<DOI>>", "10.123/aBc")
  // scalastyle:on
  val CrossrefStringWithGoodTitle = CrossrefString.replace("<<TITLE>>", "Some Title")
  val CrossrefStringWithMaximumTitle = CrossrefString.replace("<<TITLE>>", "T" * Scorable.MaxTitleLength)
  val CrossrefStringWithExcessiveTitle = CrossrefString.replace("<<TITLE>>", "T" * Scorable.MaxTitleLength + "0")
  val CrossrefStringWithNullTitle = CrossrefString.replace("\"<<TITLE>>\"", "null")
  val CrossrefStringWithEmptyTitle = CrossrefString.replace("<<TITLE>>", "")
  val CrossrefStringWithoutTitle = CrossrefString.replace("title", "nottitle")
  val MalformedCrossrefString = CrossrefString.replace("}", "")
  val CrossrefStringWithNoAuthors = CrossrefString.replace("<<TITLE>>", "Some Valid Title").replace("author", "no-author")
  val CrossrefStringWrongType = CrossrefString.replace("<<TITLE>>", "Some Valid Title").replace("journal-article", "other")
  val CrossrefStringNoType = CrossrefString.replace("<<TITLE>>", "Some Valid Title").replace("type", "not-type")

  // Unit tests
  "CrossrefScorable.jsonToMapFeatures()" should "handle invalid JSON" in {
    CrossrefScorable.jsonToMapFeatures(MalformedCrossrefString) should be (None)
  }

  it should "handle missing title" in {
    CrossrefScorable.jsonToMapFeatures(CrossrefStringWithoutTitle) should be (None)
  }

  it should "handle null title" in {
    CrossrefScorable.jsonToMapFeatures(CrossrefStringWithNullTitle) should be (None)
  }

  it should "handle empty title" in {
    CrossrefScorable.jsonToMapFeatures(CrossrefStringWithEmptyTitle) should be (None)
  }

  it should "handle subtitle" in {
    CrossrefScorable.jsonToMapFeatures(
      """{"title": ["short but not too short"], "subtitle": ["just right!"], "DOI": "10.123/asdf", "type":"journal-article","author":[{ "given" : "W", "family" : "Gaier"}]}""") match {
      case None => fail()
      case Some(result) => result.slug shouldBe "shortbutnottooshortjustright"
    }
  }

  it should "handle empty subtitle" in {
    CrossrefScorable.jsonToMapFeatures(
      """{"title": ["short but not too short"], "subtitle": [""], "DOI": "10.123/asdf", "type":"journal-article", "author":[{ "given" : "W", "family" : "Gaier"}]}""") match {
      case None => fail()
      case Some(result) => result.slug shouldBe "shortbutnottooshort"
    }
  }

  it should "handle null subtitle" in {
    CrossrefScorable.jsonToMapFeatures(
      """{"title": ["short but not too short"], "subtitle": [null], "DOI": "10.123/asdf", "type":"journal-article", "author":[{ "given" : "W", "family" : "Gaier"}]}""") match {
      case None => fail()
      case Some(result) => result.slug shouldBe "shortbutnottooshort"
    }
  }

  it should "handle missing authors" in {
    CrossrefScorable.jsonToMapFeatures(CrossrefStringWithNoAuthors) should be (None)
  }

  it should "handle valid input" in {
    CrossrefScorable.jsonToMapFeatures(CrossrefStringWithGoodTitle) match {
      case None => fail()
      case Some(result) => {
        result.slug shouldBe "sometitle"
        Scorable.jsonToMap(result.json) match {
          case None => fail()
          case Some(map) => {
            map("title").asInstanceOf[String] shouldBe "Some Title"
            map("doi").asInstanceOf[String] shouldBe "10.123/abc"
            // TODO: full name? not just a string?
            map("authors").asInstanceOf[List[String]] shouldBe List("Gaier")
            map("year").asInstanceOf[Double].toInt shouldBe 2002
          }
        }
      }
    }
  }

  "CrossrefScorable.keepRecord()" should "return true for valid JSON with title" in {
    CrossrefScorable.keepRecord(CrossrefStringWithGoodTitle) shouldBe true
  }

  it should "return true for valid JSON with a title of maximum permitted length" in {
    CrossrefScorable.keepRecord(CrossrefStringWithMaximumTitle) shouldBe true
  }

  it should "return false for valid JSON with excessively long title" in {
    CrossrefScorable.keepRecord(CrossrefStringWithExcessiveTitle) shouldBe false
  }

  it should "return false for valid JSON with null title" in {
    CrossrefScorable.keepRecord(CrossrefStringWithNullTitle) shouldBe false
  }

  it should "return false for valid JSON with no title" in {
    CrossrefScorable.keepRecord(CrossrefStringWithoutTitle) shouldBe false
  }

  it should "return false for invalid JSON" in {
    CrossrefScorable.keepRecord(CrossrefStringWithoutTitle) shouldBe false
  }

  it should "handle content types" in {
    CrossrefScorable.jsonToMapFeatures(CrossrefStringWrongType) should be (None)
    CrossrefScorable.jsonToMapFeatures(CrossrefStringNoType) should be (None)
  }
}
